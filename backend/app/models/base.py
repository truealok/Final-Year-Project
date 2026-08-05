"""Declarative base and shared model mixins (UUID PK, timestamps)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC now (used for all timestamp defaults)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Project-wide declarative base."""


class UUIDMixin:
    """UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """``created_at`` / ``updated_at`` audit columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
