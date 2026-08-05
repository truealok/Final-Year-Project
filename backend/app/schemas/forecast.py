"""Forecast schemas.

Note: ``protected_namespaces=()`` disables Pydantic's ``model_`` prefix
warning for fields like ``model_used``.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ForecastModel
from app.schemas.product import ProductBrief
from app.schemas.warehouse import WarehouseBrief


class ForecastPredictRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    start_date: date
    end_date: date
    model: ForecastModel = ForecastModel.PROPHET

    @model_validator(mode="after")
    def validate_range(self) -> "ForecastPredictRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > 365:
            raise ValueError("forecast horizon cannot exceed 365 days")
        return self


class ForecastPoint(BaseModel):
    date: date
    predicted_demand: float
    lower_bound: float
    upper_bound: float


class ForecastPredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    forecast_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    model_used: str
    prediction_date: datetime
    confidence_level: float
    points: list[ForecastPoint]
    metrics: dict[str, Any]


class ForecastHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    product: ProductBrief
    warehouse: WarehouseBrief
    model_used: str
    start_date: date
    end_date: date
    confidence_level: float
    forecast_data: list[dict[str, Any]]
    metrics: dict[str, Any]
    created_at: datetime


class ForecastModelInfo(BaseModel):
    name: str
    display_name: str
    status: str = Field(description="'available' once integrated; 'planned' now")
    description: str
    metrics: dict[str, Any]
