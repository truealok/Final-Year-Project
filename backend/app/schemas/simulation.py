"""Disruption simulation schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NodeType, RiskLevel, SeverityLevel, SimulationType


class SimulationRunRequest(BaseModel):
    simulation_type: SimulationType
    severity: SeverityLevel = SeverityLevel.MEDIUM
    duration_days: int = Field(default=7, ge=1, le=365)
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    affected_node_id: uuid.UUID | None = None
    affected_node_type: NodeType | None = None
    notes: str | None = Field(default=None, max_length=500)


class AffectedNode(BaseModel):
    id: uuid.UUID | None = None
    name: str
    type: str
    impact_pct: float


class AffectedRoute(BaseModel):
    name: str
    transport_mode: str
    delay_hours: float
    status: str


class SimulationResult(BaseModel):
    simulation_id: uuid.UUID
    simulation_type: SimulationType
    severity: SeverityLevel
    duration_days: int
    probability: float
    resilience_score: float = Field(description="0-100, higher is better")
    expected_cost: float = Field(description="Estimated disruption cost in USD")
    recovery_time_days: float
    stockout_probability: float = Field(description="0-1")
    risk_level: RiskLevel
    affected_nodes: list[AffectedNode]
    affected_routes: list[AffectedRoute]
    created_at: datetime


class SimulationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_type: SimulationType
    severity: SeverityLevel
    duration_days: int
    probability: float
    resilience_score: float
    expected_cost: float
    recovery_time_days: float
    stockout_probability: float
    risk_level: RiskLevel
    results: dict[str, Any]
    created_at: datetime
