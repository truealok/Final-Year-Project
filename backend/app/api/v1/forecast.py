"""Forecast endpoints (mock engine; ML models plug in later)."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, ForecastServiceDep
from app.schemas.common import Page
from app.schemas.forecast import (
    ForecastHistoryRead,
    ForecastModelInfo,
    ForecastPredictRequest,
    ForecastPredictResponse,
)
from app.utils.pagination import Pagination

router = APIRouter()


@router.post(
    "/predict",
    response_model=ForecastPredictResponse,
    status_code=status.HTTP_201_CREATED,
)
async def predict(
    data: ForecastPredictRequest,
    user: CurrentUser,
    service: ForecastServiceDep,
) -> ForecastPredictResponse:
    """Generate a demand forecast for a product at a warehouse.

    Currently powered by a realistic mock engine; the response contract is
    final and will not change when Prophet/XGBoost/LSTM are integrated.
    """
    return await service.predict(data, user.id)


@router.get("/history", response_model=Page[ForecastHistoryRead])
async def history(
    _user: CurrentUser,
    service: ForecastServiceDep,
    params: Pagination,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
) -> Page[ForecastHistoryRead]:
    """List past forecast runs, optionally filtered by product/warehouse."""
    items, total = await service.history(
        params, product_id=product_id, warehouse_id=warehouse_id
    )
    return Page.build(
        [ForecastHistoryRead.model_validate(f) for f in items],
        total,
        params.page,
        params.size,
    )


@router.get("/models", response_model=list[ForecastModelInfo])
async def models(
    _user: CurrentUser, service: ForecastServiceDep
) -> list[ForecastModelInfo]:
    """List available forecasting models and their evaluation metrics."""
    return service.models()
