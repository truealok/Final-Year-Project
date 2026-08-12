"""Forecast business logic.

Prediction routing (API contract identical either way):

1. **Real ML engine** (``app/services/ml/adapter.py`` → the ``ml`` package):
   used for prophet/xgboost when a trained model exists for the product.
   Metrics are real held-out validation errors (``metrics.engine == "ml"``).
2. **Mock fallback** (``_generate_points``): deterministic simulated output
   for untrained products and for LSTM (intentionally not implemented).
   Marked with ``metrics.engine == "mock"`` and ``simulated: True``.
"""

import math
import random
import uuid
from datetime import date, timedelta
from typing import Any

from app.models.forecast_history import ForecastHistory
from app.repositories.forecast_repository import (
    FORECAST_LOAD_OPTIONS,
    ForecastRepository,
)
from app.services.ml import ml_engine
from app.repositories.product_repository import ProductRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.forecast import (
    ForecastModelInfo,
    ForecastPoint,
    ForecastPredictRequest,
    ForecastPredictResponse,
)
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PaginationParams

# Mild weekly seasonality profile (Mon..Sun demand multipliers).
_WEEKDAY_FACTORS = [1.05, 1.0, 0.98, 1.02, 1.15, 1.25, 0.85]


class ForecastService:
    def __init__(
        self,
        forecasts: ForecastRepository,
        products: ProductRepository,
        warehouses: WarehouseRepository,
    ) -> None:
        self.forecasts = forecasts
        self.products = products
        self.warehouses = warehouses

    # ------------------------------------------------------------------ #
    # Mock generation (swap for a real model adapter later)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _generate_points(
        request: ForecastPredictRequest,
    ) -> tuple[list[ForecastPoint], dict[str, Any]]:
        """Produce a deterministic, realistic-looking demand forecast."""
        seed = (
            f"{request.product_id}:{request.warehouse_id}:"
            f"{request.start_date}:{request.end_date}:{request.model.value}"
        )
        rng = random.Random(seed)

        base_demand = rng.uniform(60, 420)
        daily_trend = rng.uniform(-0.15, 0.45)
        noise_scale = base_demand * 0.06
        ci_width = base_demand * rng.uniform(0.10, 0.18)

        points: list[ForecastPoint] = []
        horizon = (request.end_date - request.start_date).days + 1
        for offset in range(horizon):
            day = request.start_date + timedelta(days=offset)
            seasonal = _WEEKDAY_FACTORS[day.weekday()]
            annual = 1 + 0.12 * math.sin(2 * math.pi * day.timetuple().tm_yday / 365)
            level = (base_demand + daily_trend * offset) * seasonal * annual
            predicted = max(0.0, level + rng.gauss(0, noise_scale))
            points.append(
                ForecastPoint(
                    date=day,
                    predicted_demand=round(predicted, 1),
                    lower_bound=round(max(0.0, predicted - ci_width), 1),
                    upper_bound=round(predicted + ci_width, 1),
                )
            )

        metrics = {
            "mape": round(rng.uniform(4.5, 11.5), 2),
            "rmse": round(rng.uniform(8.0, 30.0), 2),
            "mae": round(rng.uniform(5.0, 22.0), 2),
        }
        return points, metrics

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def predict(
        self, request: ForecastPredictRequest, user_id: uuid.UUID | None
    ) -> ForecastPredictResponse:
        """Run a (mock) forecast and persist it to history."""
        if await self.products.get(request.product_id) is None:
            raise NotFoundError("Product not found.")
        if await self.warehouses.get(request.warehouse_id) is None:
            raise NotFoundError("Warehouse not found.")

        # Real ML engine first; deterministic mock as the fallback.
        ml_result = await ml_engine.predict(request)
        if ml_result is not None:
            points, metrics = ml_result
        else:
            points, metrics = self._generate_points(request)
            metrics = {**metrics, "engine": "mock", "simulated": True}
        confidence_level = 0.95

        record = await self.forecasts.create(
            product_id=request.product_id,
            warehouse_id=request.warehouse_id,
            model_used=request.model.value,
            start_date=request.start_date,
            end_date=request.end_date,
            confidence_level=confidence_level,
            forecast_data=[p.model_dump(mode="json") for p in points],
            metrics=metrics,
            created_by=user_id,
        )
        return ForecastPredictResponse(
            forecast_id=record.id,
            product_id=record.product_id,
            warehouse_id=record.warehouse_id,
            model_used=record.model_used,
            prediction_date=record.created_at,
            confidence_level=confidence_level,
            points=points,
            metrics=metrics,
        )

    async def history(
        self,
        params: PaginationParams,
        *,
        product_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
    ) -> tuple[list[ForecastHistory], int]:
        where = []
        if product_id:
            where.append(ForecastHistory.product_id == product_id)
        if warehouse_id:
            where.append(ForecastHistory.warehouse_id == warehouse_id)
        return await self.forecasts.list(
            offset=params.offset,
            limit=params.size,
            where=where,
            options=FORECAST_LOAD_OPTIONS,
        )

    @staticmethod
    def models() -> list[ForecastModelInfo]:
        """Describe the forecasting models.

        prophet/xgboost report ``status="available"`` with **real averaged
        validation metrics** once trained models exist in the ML registry;
        until then they are ``"planned"`` with placeholder numbers (marked
        ``simulated``). LSTM is intentionally not implemented.
        """
        real = ml_engine.models_info()

        def info(
            name: str, display: str, description: str, placeholder: dict
        ) -> ForecastModelInfo:
            trained = real.get(name)
            if trained:
                return ForecastModelInfo(
                    name=name,
                    display_name=display,
                    status="available",
                    description=(
                        f"{description} Trained on {trained['n_series']} "
                        "series; metrics are averaged held-out validation "
                        "errors."
                    ),
                    metrics={
                        "mape": trained["mape"],
                        "rmse": trained["rmse"],
                        "mae": trained["mae"],
                        "wape": trained.get("wape"),
                        "smape": trained.get("smape"),
                        "n_series": trained["n_series"],
                        "last_trained": trained.get("last_trained"),
                    },
                )
            return ForecastModelInfo(
                name=name,
                display_name=display,
                status="planned",
                description=(
                    f"{description} No trained model yet; predictions are "
                    "currently simulated."
                ),
                metrics={**placeholder, "simulated": True, "last_trained": None},
            )

        return [
            info(
                "prophet",
                "Prophet",
                "Additive time-series model for trend + seasonality.",
                {"mape": 7.8, "rmse": 18.4, "mae": 13.2},
            ),
            info(
                "xgboost",
                "XGBoost",
                "Gradient-boosted trees over engineered demand features.",
                {"mape": 6.9, "rmse": 16.1, "mae": 11.8},
            ),
            ForecastModelInfo(
                name="lstm",
                display_name="LSTM",
                status="planned",
                description=(
                    "Recurrent neural network for sequential demand patterns. "
                    "Integration pending; predictions are currently simulated."
                ),
                metrics={"mape": 8.4, "rmse": 19.7, "mae": 14.5,
                         "simulated": True, "last_trained": None},
            ),
        ]
