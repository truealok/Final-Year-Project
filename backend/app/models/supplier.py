"""Supplier model (root of the supply chain network)."""

from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EntityStatus, RiskLevel, enum_column

if TYPE_CHECKING:
    from app.models.factory import Factory


class Supplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    country: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reliability_score: Mapped[float] = mapped_column(
        Float, default=85.0, nullable=False
    )  # 0-100
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel), default=RiskLevel.MEDIUM, nullable=False
    )
    status: Mapped[EntityStatus] = mapped_column(
        enum_column(EntityStatus), default=EntityStatus.ACTIVE, nullable=False
    )

    factories: Mapped[list["Factory"]] = relationship(back_populates="supplier")
