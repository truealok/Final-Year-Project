"""Analytics business logic - trends aggregated from real data where it
exists (sales, suppliers, warehouses, simulations) with deterministic mock
series for metrics whose engines are not integrated yet."""

import random
from collections import defaultdict
from datetime import date, timedelta

from app.repositories.inventory_repository import InventoryRepository
from app.repositories.sales_repository import SalesRepository
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.analytics import (
    AnalyticsResponse,
    SupplierPerformance,
    TrendPoint,
    WarehouseUtilization,
)


def _last_12_month_keys() -> list[str]:
    today = date.today().replace(day=1)
    keys: list[str] = []
    year, month = today.year, today.month
    for _ in range(12):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(keys))


def _mock_series(seed: str, low: float, high: float) -> list[TrendPoint]:
    rng = random.Random(seed)
    return [
        TrendPoint(period=key, value=round(rng.uniform(low, high), 1))
        for key in _last_12_month_keys()
    ]


class AnalyticsService:
    def __init__(
        self,
        sales: SalesRepository,
        suppliers: SupplierRepository,
        warehouses: WarehouseRepository,
        inventory: InventoryRepository,
        simulations: SimulationRepository,
    ) -> None:
        self.sales = sales
        self.suppliers = suppliers
        self.warehouses = warehouses
        self.inventory = inventory
        self.simulations = simulations

    async def _demand_trend(self) -> list[TrendPoint]:
        since = date.today() - timedelta(days=365)
        rows = await self.sales.daily_totals(since=since)
        if not rows:
            return _mock_series("demand", 40_000, 95_000)
        monthly: dict[str, float] = defaultdict(float)
        for day, quantity, _revenue in rows:
            monthly[f"{day.year:04d}-{day.month:02d}"] += quantity
        return [
            TrendPoint(period=key, value=round(value, 1))
            for key, value in sorted(monthly.items())
        ]

    async def _disruption_frequency(self) -> list[TrendPoint]:
        simulations = await self.simulations.recent(500)
        if not simulations:
            return _mock_series("disruptions", 1, 9)
        monthly: dict[str, int] = defaultdict(int)
        for sim in simulations:
            key = f"{sim.created_at.year:04d}-{sim.created_at.month:02d}"
            monthly[key] += 1
        return [
            TrendPoint(period=key, value=float(count))
            for key, count in sorted(monthly.items())
        ]

    async def _supplier_performance(self) -> list[SupplierPerformance]:
        result = []
        for supplier in await self.suppliers.top_by_reliability(10):
            rng = random.Random(str(supplier.id))
            result.append(
                SupplierPerformance(
                    id=supplier.id,
                    name=supplier.name,
                    reliability_score=supplier.reliability_score,
                    on_time_delivery_rate=round(
                        supplier.reliability_score * rng.uniform(0.9, 1.0), 1
                    ),
                    avg_lead_time_days=float(supplier.lead_time_days),
                    risk_level=supplier.risk_level,
                )
            )
        return result

    async def _warehouse_utilization(self) -> list[WarehouseUtilization]:
        quantities = await self.inventory.quantity_by_warehouse()
        result = []
        for warehouse in await self.warehouses.list_all():
            units = quantities.get(warehouse.id, 0)
            result.append(
                WarehouseUtilization(
                    id=warehouse.id,
                    name=warehouse.name,
                    capacity=warehouse.capacity,
                    current_inventory=units,
                    utilization_pct=(
                        round(units / warehouse.capacity * 100, 1)
                        if warehouse.capacity
                        else 0.0
                    ),
                    status=warehouse.status.value,
                )
            )
        return result

    async def overview(self) -> AnalyticsResponse:
        inventory_summary = await self.inventory.summary()
        total_units = float(inventory_summary["total_units"]) or 500_000.0
        return AnalyticsResponse(
            demand_trend=await self._demand_trend(),
            inventory_trend=_mock_series(
                "inventory", total_units * 0.85, total_units * 1.15
            ),
            supplier_performance=await self._supplier_performance(),
            warehouse_utilization=await self._warehouse_utilization(),
            disruption_frequency=await self._disruption_frequency(),
            recovery_trend=_mock_series("recovery", 3.5, 12.0),
            carbon_emissions=_mock_series("carbon", 90, 160),
        )
