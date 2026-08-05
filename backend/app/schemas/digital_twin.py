"""Digital twin network schemas (nodes + edges graph)."""

import uuid

from pydantic import BaseModel

from app.models.enums import NodeType, RiskLevel


class NetworkNode(BaseModel):
    id: uuid.UUID
    name: str
    type: NodeType
    status: str
    country: str | None = None
    city: str | None = None
    capacity: int | None = None
    current_inventory: int | None = None
    utilization_pct: float | None = None
    risk_level: RiskLevel


class NetworkEdge(BaseModel):
    id: uuid.UUID
    source: uuid.UUID
    target: uuid.UUID
    transport_mode: str
    distance_km: float
    transit_time_hours: float
    status: str
    risk_level: RiskLevel


class NetworkSummary(BaseModel):
    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]
    overall_risk: RiskLevel
    resilience_score: float


class NetworkResponse(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    summary: NetworkSummary
