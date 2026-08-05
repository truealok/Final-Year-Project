"""Supplier schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import EntityStatus, RiskLevel


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    contact_email: EmailStr | None = None
    reliability_score: float = Field(default=85.0, ge=0, le=100)
    lead_time_days: int = Field(default=7, ge=0, le=365)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    status: EntityStatus = EntityStatus.ACTIVE


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    country: str | None = Field(default=None, min_length=1, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    contact_email: EmailStr | None = None
    reliability_score: float | None = Field(default=None, ge=0, le=100)
    lead_time_days: int | None = Field(default=None, ge=0, le=365)
    risk_level: RiskLevel | None = None
    status: EntityStatus | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
