"""Dashboard business logic - aggregates KPIs from real data + mock metrics."""

import random
from datetime import date

from app.repositories.alert_repository import AlertRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.alert import AlertRead
from app.schemas.dashboard import (
    CarbonEmissions,
    DashboardResponse,
    InventorySnapshot,
)
from app.schemas.simulation import SimulationHistoryRead


class DashboardService:
    def __init__(
        self,
        alerts: AlertRepository,
        simulations: SimulationRepository,
        inventory: InventoryRepository,
    ) -> None:
        self.alerts = alerts
        self.simulations = simulations
        self.inventory = inventory

    async def overview(self) -> DashboardResponse:
        """Build the dashboard snapshot.

        Simulation-derived KPIs come from recent runs when available;
        forecast accuracy and carbon metrics are deterministic mock values
        until the ML services are integrated.
        """
        # Deterministic per-day mock so the UI is stable within a day.
        rng = random.Random(date.today().toordinal())

        recent_sims = await self.simulations.recent(5)
        if recent_sims:
            resilience = round(
                sum(s.resilience_score for s in recent_sims) / len(recent_sims), 1
            )
            expected_cost = round(recent_sims[0].expected_cost, 2)
            stockout = round(
                sum(s.stockout_probability for s in recent_sims)
                / len(recent_sims),
                3,
            )
            recovery = round(
                sum(s.recovery_time_days for s in recent_sims)
                / len(recent_sims),
                1,
            )
        else:
            resilience = round(rng.uniform(72, 84), 1)
            expected_cost = round(rng.uniform(180_000, 420_000), 2)
            stockout = round(rng.uniform(0.06, 0.18), 3)
            recovery = round(rng.uniform(4, 11), 1)

        inventory_summary = await self.inventory.summary()
        latest_alerts = await self.alerts.latest(5)

        return DashboardResponse(
            forecast_accuracy=round(rng.uniform(85.5, 93.5), 1),
            resilience_score=resilience,
            expected_cost=expected_cost,
            current_inventory=InventorySnapshot(
                total_units=int(inventory_summary["total_units"]),
                total_value=float(inventory_summary["total_value"]),
                low_stock_items=int(inventory_summary["low_stock_items"]),
                out_of_stock_items=int(inventory_summary["out_of_stock_items"]),
            ),
            stockout_probability=stockout,
            recovery_time_days=recovery,
            carbon_emissions=CarbonEmissions(
                total_tons_co2=round(rng.uniform(950, 1450), 1),
                change_pct=round(rng.uniform(-8.0, 4.0), 1),
            ),
            latest_alerts=[AlertRead.model_validate(a) for a in latest_alerts],
            recent_simulations=[
                SimulationHistoryRead.model_validate(s) for s in recent_sims
            ],
        )
