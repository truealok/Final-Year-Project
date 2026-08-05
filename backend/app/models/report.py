"""Generated report model (forecast / simulation / inventory / risk)."""

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ReportFormat, ReportType, enum_column


class Report(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reports"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(
        enum_column(ReportType), nullable=False
    )
    format: Mapped[ReportFormat] = mapped_column(
        enum_column(ReportFormat), default=ReportFormat.JSON, nullable=False
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # {"columns": [...], "rows": [[...], ...], "summary": {...}}
    content: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="completed", nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
