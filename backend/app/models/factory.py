"""Factory model (supplied by a Supplier, feeds Warehouses)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EntityStatus, enum_column

if TYPE_CHECKING:
    from app.models.supplier import Supplier
    from app.models.warehouse import Warehouse


class Factory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "factories"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    capacity_per_day: Mapped[int] = mapped_column(
        Integer, default=1000, nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[EntityStatus] = mapped_column(
        enum_column(EntityStatus), default=EntityStatus.ACTIVE, nullable=False
    )

    supplier: Mapped["Supplier | None"] = relationship(
        back_populates="factories", lazy="selectin"
    )
    warehouses: Mapped[list["Warehouse"]] = relationship(back_populates="factory")
