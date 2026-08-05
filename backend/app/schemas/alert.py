"""Alert schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AlertSeverity


class AlertCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    severity: AlertSeverity = AlertSeverity.INFO
    source: str | None = Field(default=None, max_length=120)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    severity: AlertSeverity
    source: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    is_read: bool
    created_at: datetime
    updated_at: datetime


class AlertSummary(BaseModel):
    total: int
    unread: int
    critical: int
    warning: int
    info: int
