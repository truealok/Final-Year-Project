"""Warehouse model (fed by a Factory, serves Retail Stores, holds Inventory)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EntityStatus, enum_column

if TYPE_CHECKING:
    from app.models.factory import Factory
    from app.models.forecast_history import ForecastHistory
    from app.models.inventory import Inventory
    from app.models.retail_store import RetailStore


class Warehouse(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=100_000, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    factory_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("factories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[EntityStatus] = mapped_column(
        enum_column(EntityStatus), default=EntityStatus.ACTIVE, nullable=False
    )

    factory: Mapped["Factory | None"] = relationship(
        back_populates="warehouses", lazy="selectin"
    )
    retail_stores: Mapped[list["RetailStore"]] = relationship(
        back_populates="warehouse"
    )
    inventory_items: Mapped[list["Inventory"]] = relationship(
        back_populates="warehouse", cascade="all, delete-orphan"
    )
    forecasts: Mapped[list["ForecastHistory"]] = relationship(
        back_populates="warehouse", cascade="all, delete-orphan"
    )
