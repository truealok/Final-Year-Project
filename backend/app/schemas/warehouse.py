"""Warehouse schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityStatus


class WarehouseBrief(BaseModel):
    """Minimal warehouse reference embedded in other resources."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class WarehouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    capacity: int = Field(default=100_000, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: EntityStatus = EntityStatus.ACTIVE


class WarehouseCreate(WarehouseBase):
    factory_id: uuid.UUID | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    capacity: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: EntityStatus | None = None
    factory_id: uuid.UUID | None = None


class WarehouseRead(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    factory_id: uuid.UUID | None = None
    current_inventory: int = 0
    utilization_pct: float = 0.0
    created_at: datetime
    updated_at: datetime
