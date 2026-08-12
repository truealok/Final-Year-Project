"""Prediction pipeline — the ML module's public inference API.

``predict_demand`` loads a trained model from the registry and produces a
structured forecast. Design rules:

- **Train once, predict many**: nothing is retrained here; models are loaded
  from disk (with a small in-process cache) and the dataset is only read for
  XGBoost's feature history (also cached).
- **Series resolution**: a (product, warehouse) model is used when one was
  trained; otherwise the product-level model serves the request and
  ``series_level: "product"`` says so. Warehouse signal is never fabricated.
- Clear errors: :class:`ModelNotTrainedError`, :class:`UnknownSeriesError`,
  :class:`InsufficientHistoryError`.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta
from typing import Any

import pandas as pd

from ml.config import ConfigDict, load_config, resolve_path
from ml.data.loaders import normalize_id
from ml.data.preprocessing import get_series
from ml.exceptions import ModelNotTrainedError
from ml.modeling.registry import ModelRegistry, make_series_key
from ml.modeling.xgboost_model import XGBForecaster
from ml.pipeline.dataset import load_dataset

_MODEL_CACHE: dict[tuple[str, str, int], Any] = {}


def get_registry(cfg: ConfigDict | None = None) -> ModelRegistry:
    cfg = cfg or load_config()
    return ModelRegistry(
        resolve_path(cfg.paths.models_dir), resolve_path(cfg.paths.artifacts_dir)
    )


def _resolve_series(
    registry: ModelRegistry, product_id: str, warehouse_id: str | None
) -> tuple[str, str]:
    """Pick the series key to serve from: (series_key, series_level)."""
    if warehouse_id:
        pw_key = make_series_key(product_id, warehouse_id)
        if registry.has_series(pw_key):
            return pw_key, "product_warehouse"
    p_key = make_series_key(product_id)
    if registry.has_series(p_key):
        return p_key, "product"
    raise ModelNotTrainedError(
        f"No trained model for product {product_id}"
        + (f" (warehouse {warehouse_id})" if warehouse_id else "")
        + ". Train it with: python -m ml.train --product " + str(product_id)
    )


def _load_model(
    registry: ModelRegistry, series_key: str, model_type: str | None
) -> tuple[Any, dict[str, Any]]:
    """Load (with cache) the best or explicitly requested model."""
    if model_type is None:
        best = registry.best_info(series_key)
        model_type = best["model_type"]
        version = best["version"]
    else:
        version = None  # latest of that type; raises if never trained

    if version is not None:
        cache_key = (series_key, model_type, version)
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

    model, metadata = registry.load(series_key, model_type, version)
    cache_key = (series_key, metadata["model_type"], metadata["version"])
    _MODEL_CACHE[cache_key] = (model, metadata)
    return model, metadata


def clear_model_cache() -> None:
    _MODEL_CACHE.clear()


def predict_demand(
    product_id: str,
    warehouse_id: str | None = None,
    forecast_days: int | None = None,
    start_date: str | date_cls | None = None,
    end_date: str | date_cls | None = None,
    model_type: str | None = None,
    cfg: ConfigDict | None = None,
) -> dict[str, Any]:
    """Forecast demand for a product (optionally at a warehouse).

    Date selection: either ``start_date``+``end_date``, or ``forecast_days``
    from the day after the last observed date (default: config horizon).
    """
    cfg = cfg or load_config()
    registry = get_registry(cfg)

    pid = normalize_id(product_id)
    wid = normalize_id(warehouse_id) if warehouse_id else None
    if pid is None:
        raise ModelNotTrainedError("product_id is required")

    series_key, series_level = _resolve_series(registry, pid, wid)
    model, metadata = _load_model(registry, series_key, model_type)
    model_used = metadata["model_type"]

    # ---- forecast dates ---------------------------------------------- #
    if start_date is not None and end_date is not None:
        dates = pd.date_range(
            pd.Timestamp(start_date), pd.Timestamp(end_date), freq="D"
        )
        if len(dates) == 0:
            raise ValueError("end_date must be on or after start_date")
    else:
        horizon = int(forecast_days or cfg.forecast.horizon_days)
        anchor = pd.Timestamp(metadata.get("history_end"))
        dates = pd.date_range(
            anchor + timedelta(days=1), periods=horizon, freq="D"
        )

    # ---- run the model ------------------------------------------------ #
    if isinstance(model, XGBForecaster):
        df, _, _ = load_dataset(cfg, validate=False, use_cache=True)
        history = get_series(
            df, pid, wid if series_level == "product_warehouse" else None
        )
        pred = model.predict_recursive(history, dates)
    else:
        pred = model.predict(dates)

    display = {"prophet": "Prophet", "xgboost": "XGBoost"}.get(
        model_used, model_used
    )
    return {
        "product_id": pid,
        # per spec §15: never fabricate warehouse-level output — null unless
        # an actual warehouse-level model served the request
        "warehouse_id": wid if series_level == "product_warehouse" else None,
        "requested_warehouse_id": wid,
        "series_level": series_level,
        "model": display,
        "model_version": metadata["version"],
        "trained_at": metadata.get("saved_at"),
        "dataset_version": metadata.get("dataset_version"),
        "confidence_level": metadata.get(
            "confidence_level", float(cfg.forecast.confidence_level)
        ),
        "metrics": metadata.get("metrics", {}),
        "metrics_source": metadata.get("metrics_source"),
        "forecast": [
            {
                "date": str(row.date.date()),
                "predicted_demand": round(float(row.yhat), 1),
                "lower_bound": round(float(row.yhat_lower), 1),
                "upper_bound": round(float(row.yhat_upper), 1),
            }
            for row in pred.itertuples()
        ],
    }
