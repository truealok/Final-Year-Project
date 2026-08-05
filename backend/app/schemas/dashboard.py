"""Dashboard KPI schemas."""

from pydantic import BaseModel, Field

from app.schemas.alert import AlertRead
from app.schemas.simulation import SimulationHistoryRead


class InventorySnapshot(BaseModel):
    total_units: int
    total_value: float
    low_stock_items: int
    out_of_stock_items: int


class CarbonEmissions(BaseModel):
    total_tons_co2: float
    change_pct: float = Field(description="Change vs previous period (%)")


class DashboardResponse(BaseModel):
    forecast_accuracy: float = Field(description="Overall forecast accuracy (%)")
    resilience_score: float = Field(description="Network resilience 0-100")
    expected_cost: float = Field(description="Expected disruption cost (USD)")
    current_inventory: InventorySnapshot
    stockout_probability: float = Field(description="0-1")
    recovery_time_days: float
    carbon_emissions: CarbonEmissions
    latest_alerts: list[AlertRead]
    recent_simulations: list[SimulationHistoryRead]
