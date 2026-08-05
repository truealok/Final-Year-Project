"""Persisted disruption simulation runs (mock engine today, Monte Carlo later)."""

import uuid
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    RiskLevel,
    SeverityLevel,
    SimulationType,
    enum_column,
)


class SimulationHistory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "simulation_history"

    simulation_type: Mapped[SimulationType] = mapped_column(
        enum_column(SimulationType), nullable=False
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        enum_column(SeverityLevel), default=SeverityLevel.MEDIUM, nullable=False
    )
    duration_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    affected_node_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    affected_node_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Outcome metrics.
    resilience_score: Mapped[float] = mapped_column(Float, nullable=False)
    expected_cost: Mapped[float] = mapped_column(Float, nullable=False)
    recovery_time_days: Mapped[float] = mapped_column(Float, nullable=False)
    stockout_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel), default=RiskLevel.MEDIUM, nullable=False
    )
    results: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
