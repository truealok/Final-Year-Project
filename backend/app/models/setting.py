"""Key/value application settings stored in the database."""

from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Setting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    value: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
