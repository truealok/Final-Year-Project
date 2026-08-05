"""Historical daily sales - the source data for demand forecasting."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.retail_store import RetailStore


class SalesHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sales_history"
    __table_args__ = (
        Index("ix_sales_history_product_date", "product_id", "date"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    retail_store_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retail_stores.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="sales")
    retail_store: Mapped["RetailStore"] = relationship(back_populates="sales")
