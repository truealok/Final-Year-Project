"""Product (SKU) model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.forecast_history import ForecastHistory
    from app.models.inventory import Inventory
    from app.models.sales_history import SalesHistory


class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="unit", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category | None"] = relationship(
        back_populates="products", lazy="selectin"
    )
    inventory_items: Mapped[list["Inventory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    sales: Mapped[list["SalesHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    forecasts: Mapped[list["ForecastHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
