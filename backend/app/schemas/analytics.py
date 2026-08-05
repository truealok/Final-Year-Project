"""Analytics schemas."""

import uuid

from pydantic import BaseModel

from app.models.enums import RiskLevel


class TrendPoint(BaseModel):
    period: str  # "YYYY-MM"
    value: float


class SupplierPerformance(BaseModel):
    id: uuid.UUID
    name: str
    reliability_score: float
    on_time_delivery_rate: float
    avg_lead_time_days: float
    risk_level: RiskLevel


class WarehouseUtilization(BaseModel):
    id: uuid.UUID
    name: str
    capacity: int
    current_inventory: int
    utilization_pct: float
    status: str


class AnalyticsResponse(BaseModel):
    demand_trend: list[TrendPoint]
    inventory_trend: list[TrendPoint]
    supplier_performance: list[SupplierPerformance]
    warehouse_utilization: list[WarehouseUtilization]
    disruption_frequency: list[TrendPoint]
    recovery_trend: list[TrendPoint]
    carbon_emissions: list[TrendPoint]
