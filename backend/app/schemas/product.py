"""Product and category schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None


class ProductBrief(BaseModel):
    """Minimal product reference embedded in other resources."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    description: str | None = None
    category: CategoryRead | None = None
    unit_cost: float
    unit_price: float
    unit: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
