"""Dashboard business logic — every KPI is computed, none are random.

Sources per KPI:

- forecast accuracy   → ML registry (100 − mean validation WAPE across
                        trained models; ``0`` and clearly absent when no
                        model is trained yet)
- resilience / cost / stockout / recovery
                      → recent Monte Carlo simulation runs when available,
                        else derived from the live network snapshot
                        (inventory cover vs demand, supplier lead times)
- inventory snapshot  → inventory table aggregates
- carbon emissions    → configured per-mode emission factors applied to the
                        network's current demand flows (30-day estimate);
                        change % = real sales-volume change month over month
- alerts / simulations → latest database records
"""

from app.repositories.alert_repository import AlertRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.sales_repository import SalesRepository
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.alert import AlertRead
from app.schemas.dashboard import (
    CarbonEmissions,
    DashboardResponse,
    InventorySnapshot,
)
from app.schemas.simulation import SimulationHistoryRead
from app.services.digital_twin_service import DigitalTwinService
from app.services.ml import ml_engine
from app.services.twin_graph import route_emissions_kg_per_day


class DashboardService:
    def __init__(
        self,
        alerts: AlertRepository,
        simulations: SimulationRepository,
        inventory: InventoryRepository,
        sales: SalesRepository,
        twin: DigitalTwinService,
    ) -> None:
        self.alerts = alerts
        self.simulations = simulations
        self.inventory = inventory
        self.sales = sales
        self.twin = twin

    @staticmethod
    def _forecast_accuracy() -> float:
        """100 − mean validation WAPE of trained models (0 when untrained)."""
        info = ml_engine.models_info()
        wapes = [
            m["wape"] for m in info.values() if m.get("wape") is not None
        ]
        if not wapes:
            return 0.0
        return round(max(0.0, 100.0 - sum(wapes) / len(wapes)), 1)

    async def overview(self) -> DashboardResponse:
        """Build the dashboard snapshot from live data."""
        snap = await self.twin.snapshot()
        recent_sims = await self.simulations.recent(5)

        if recent_sims:
            resilience = round(
                sum(s.resilience_score for s in recent_sims) / len(recent_sims),
                1,
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
            # No simulations yet → derive from the network snapshot.
            resilience = snap.resilience_score
            expected_cost = 0.0
            from app.models.enums import NodeType

            warehouses = [
                n for n in snap.by_type(NodeType.WAREHOUSE)
                if n.daily_demand > 0
            ]
            # share of demand-bearing warehouses with < 7 days of cover
            thin = [
                w for w in warehouses
                if w.cover_days is not None and w.cover_days < 7
            ]
            stockout = round(len(thin) / len(warehouses), 3) if warehouses else 0.0
            supplier_leads = [
                n.lead_time_days
                for n in snap.by_type(NodeType.SUPPLIER)
                if n.lead_time_days
            ]
            recovery = round(
                sum(supplier_leads) / len(supplier_leads), 1
            ) if supplier_leads else 0.0

        # ---- carbon: configured factors x current demand flows -------- #
        kg_per_day = route_emissions_kg_per_day(snap)
        month_tons = round(kg_per_day * 30 / 1000, 1)
        # real month-over-month sales volume change drives the trend
        totals = await self.sales.product_window_totals(30)
        last = sum(t[1] for t in totals)
        prev = sum(t[2] for t in totals)
        change_pct = round((last - prev) / prev * 100, 1) if prev else 0.0

        inventory_summary = await self.inventory.summary()
        latest_alerts = await self.alerts.latest(5)

        return DashboardResponse(
            forecast_accuracy=self._forecast_accuracy(),
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
                total_tons_co2=month_tons,
                change_pct=change_pct,
            ),
            latest_alerts=[AlertRead.model_validate(a) for a in latest_alerts],
            recent_simulations=[
                SimulationHistoryRead.model_validate(s) for s in recent_sims
            ],
        )
