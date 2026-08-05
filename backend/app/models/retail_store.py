"""Retail store model (served by a Warehouse, generates Sales)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EntityStatus, enum_column

if TYPE_CHECKING:
    from app.models.sales_history import SalesHistory
    from app.models.warehouse import Warehouse


class RetailStore(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "retail_stores"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[EntityStatus] = mapped_column(
        enum_column(EntityStatus), default=EntityStatus.ACTIVE, nullable=False
    )

    warehouse: Mapped["Warehouse | None"] = relationship(
        back_populates="retail_stores", lazy="selectin"
    )
    sales: Mapped[list["SalesHistory"]] = relationship(
        back_populates="retail_store", cascade="all, delete-orphan"
    )
