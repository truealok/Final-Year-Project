"""Report schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportFormat, ReportType


class ReportGenerateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    report_type: ReportType
    format: ReportFormat = ReportFormat.JSON
    parameters: dict[str, Any] = Field(default_factory=dict)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    report_type: ReportType
    format: ReportFormat
    status: str
    parameters: dict[str, Any]
    created_at: datetime


class ReportDetail(ReportRead):
    content: dict[str, Any]
