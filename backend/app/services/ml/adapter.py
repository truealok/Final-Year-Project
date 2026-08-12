"""ML forecast engine adapter.

Bridges ``ForecastService`` to the standalone ``ml`` package without changing
any API contract:

- ``predict(request)`` returns real ``(points, metrics)`` from a trained
  model, or ``None`` when no model is trained for the product (the caller
  then falls back to the mock engine — the platform keeps working end to end
  before/without training).
- ``models_info()`` exposes real registry aggregates for
  ``GET /forecast/models``.

The ``ml`` package import is deferred and failure-tolerant: if its
dependencies are missing the backend still boots and serves mock forecasts.
All ML work runs in a worker thread (prophet/xgboost/pandas are blocking).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import anyio.to_thread

if TYPE_CHECKING:  # pragma: no cover
    from app.schemas.forecast import ForecastPoint, ForecastPredictRequest

logger = logging.getLogger("resilichain.ml")


class MLForecastEngine:
    def __init__(self) -> None:
        self._import_failed = False

    # ------------------------------------------------------------------ #
    def _ml(self):
        """Import the ml package lazily; remember a hard failure."""
        if self._import_failed:
            return None
        try:
            import ml.pipeline.prediction as prediction

            return prediction
        except Exception as exc:  # missing deps, broken install, ...
            self._import_failed = True
            logger.warning("ML module unavailable, using mock engine: %s", exc)
            return None

    def available(self) -> bool:
        prediction = self._ml()
        if prediction is None:
            return False
        try:
            return bool(prediction.get_registry().list_series())
        except Exception as exc:
            logger.warning("ML registry unreadable: %s", exc)
            return False

    # ------------------------------------------------------------------ #
    def _predict_sync(
        self, request: "ForecastPredictRequest"
    ) -> tuple[list["ForecastPoint"], dict[str, Any]] | None:
        from app.schemas.forecast import ForecastPoint

        prediction = self._ml()
        if prediction is None:
            return None
        from ml.exceptions import MLError

        try:
            result = prediction.predict_demand(
                str(request.product_id),
                warehouse_id=str(request.warehouse_id),
                start_date=request.start_date,
                end_date=request.end_date,
                model_type=request.model.value,
            )
        except MLError as exc:
            # No trained model / not enough history → mock fallback.
            logger.info(
                "ML fallback to mock for product=%s model=%s: %s",
                request.product_id,
                request.model.value,
                exc,
            )
            return None

        points = [
            ForecastPoint(
                date=item["date"],
                predicted_demand=item["predicted_demand"],
                lower_bound=item["lower_bound"],
                upper_bound=item["upper_bound"],
            )
            for item in result["forecast"]
        ]
        model_metrics = result.get("metrics") or {}
        metrics: dict[str, Any] = {
            key: value
            for key, value in model_metrics.items()
            if value is not None
        }
        metrics.update(
            {
                "engine": "ml",
                "model_version": result["model_version"],
                "series_level": result["series_level"],
                "metrics_source": result.get("metrics_source"),
                "dataset_version": result.get("dataset_version"),
            }
        )
        return points, metrics

    async def predict(
        self, request: "ForecastPredictRequest"
    ) -> tuple[list["ForecastPoint"], dict[str, Any]] | None:
        """Async wrapper — runs the blocking ML prediction in a thread."""
        if request.model.value not in ("prophet", "xgboost"):
            return None  # LSTM is intentionally not implemented
        return await anyio.to_thread.run_sync(self._predict_sync, request)

    # ------------------------------------------------------------------ #
    def models_info(self) -> dict[str, dict[str, Any]]:
        """Per-model-type aggregates from the registry (empty dict if none).

        Metric values are averaged *real* validation metrics across trained
        series. ``mape`` falls back to sMAPE when true MAPE was undefined
        (all-zero actuals) so the dashboard's numeric contract holds.
        """
        prediction = self._ml()
        if prediction is None:
            return {}
        try:
            summary = prediction.get_registry().summary()
        except Exception as exc:
            logger.warning("ML registry summary failed: %s", exc)
            return {}
        out: dict[str, dict[str, Any]] = {}
        for model_type, info in summary.items():
            avg = info.get("avg_metrics", {})
            mape = avg.get("mape", avg.get("smape", 0.0))
            out[model_type] = {
                "mape": float(mape if mape is not None else 0.0),
                "rmse": float(avg.get("rmse") or 0.0),
                "mae": float(avg.get("mae") or 0.0),
                "wape": avg.get("wape"),
                "smape": avg.get("smape"),
                "n_series": info.get("n_series", 0),
                "last_trained": info.get("last_trained"),
            }
        return out


# Module-level singleton — stateless besides the import-failure flag.
ml_engine = MLForecastEngine()
