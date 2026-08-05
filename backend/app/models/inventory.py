"""Inventory model - stock of a product held at a warehouse."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import InventoryStatus, enum_column

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.warehouse import Warehouse


class Inventory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "warehouse_id", name="uq_inventory_product_warehouse"
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[InventoryStatus] = mapped_column(
        enum_column(InventoryStatus),
        default=InventoryStatus.IN_STOCK,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(
        back_populates="inventory_items", lazy="selectin"
    )
    warehouse: Mapped["Warehouse"] = relationship(
        back_populates="inventory_items", lazy="selectin"
    )
