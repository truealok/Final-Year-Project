"""Persisted forecast runs (mock output today, real models plug in later)."""

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.warehouse import Warehouse


class ForecastHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "forecast_history"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    confidence_level: Mapped[float] = mapped_column(
        Float, default=0.95, nullable=False
    )
    forecast_data: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    product: Mapped["Product"] = relationship(
        back_populates="forecasts", lazy="selectin"
    )
    warehouse: Mapped["Warehouse"] = relationship(
        back_populates="forecasts", lazy="selectin"
    )
