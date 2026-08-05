"""Transport route model - an edge in the supply chain network graph.

Routes connect heterogeneous node types (supplier -> factory -> warehouse ->
retail store), so endpoints are stored as ``(node_type, node_id)`` pairs
rather than hard foreign keys.
"""

import uuid

from sqlalchemy import Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    EntityStatus,
    NodeType,
    RiskLevel,
    TransportMode,
    enum_column,
)


class TransportRoute(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transport_routes"

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_type: Mapped[NodeType] = mapped_column(
        enum_column(NodeType), nullable=False
    )
    origin_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    destination_type: Mapped[NodeType] = mapped_column(
        enum_column(NodeType), nullable=False
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    transport_mode: Mapped[TransportMode] = mapped_column(
        enum_column(TransportMode), default=TransportMode.TRUCK, nullable=False
    )
    distance_km: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transit_time_hours: Mapped[float] = mapped_column(
        Float, default=24.0, nullable=False
    )
    cost_per_shipment: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    status: Mapped[EntityStatus] = mapped_column(
        enum_column(EntityStatus), default=EntityStatus.ACTIVE, nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel), default=RiskLevel.LOW, nullable=False
    )
