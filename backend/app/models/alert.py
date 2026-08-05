"""Operational alert model (critical / warning / info)."""

import uuid

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import AlertSeverity, enum_column


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        enum_column(AlertSeverity), default=AlertSeverity.INFO, nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
