"""Inventory schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import InventoryStatus
from app.schemas.product import ProductBrief
from app.schemas.warehouse import WarehouseBrief


class InventoryCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=50, ge=0)
    safety_stock: int = Field(default=25, ge=0)
    unit_cost: float = Field(default=0.0, ge=0)


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    reorder_point: int | None = Field(default=None, ge=0)
    safety_stock: int | None = Field(default=None, ge=0)
    unit_cost: float | None = Field(default=None, ge=0)


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product: ProductBrief
    warehouse: WarehouseBrief
    quantity: int
    reorder_point: int
    safety_stock: int
    unit_cost: float
    status: InventoryStatus
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def total_value(self) -> float:
        return round(self.quantity * self.unit_cost, 2)


class InventorySummary(BaseModel):
    total_items: int
    total_units: int
    total_value: float
    low_stock_items: int
    out_of_stock_items: int
