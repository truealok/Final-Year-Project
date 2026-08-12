"""Digital twin business logic — real NetworkX-backed graph analytics.

The network is assembled from database entities (suppliers, factories,
warehouses, stores, transport routes, inventory) into a shared
:class:`~app.services.twin_graph.NetworkSnapshot`. Everything shown is
**computed, not random**:

- demand per store/warehouse = trailing-window aggregates of the REAL sales
  history;
- warehouse risk = inventory cover days vs demand; factory risk = capacity
  utilization vs downstream demand; supplier risk = configured reliability;
- resilience = documented composite (redundancy, coverage, reliability,
  connectivity) computed on the NetworkX graph.

Network entities/parameters themselves are CONFIGURED (see
``scripts/seed_network.py``) — the dataset provides demand, not the network.
"""

import datetime

from app.models.enums import NodeType
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.network_repository import (
    FactoryRepository,
    RetailStoreRepository,
    TransportRouteRepository,
)
from app.repositories.sales_repository import SalesRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.digital_twin import (
    NetworkEdge,
    NetworkNode,
    NetworkResponse,
    NetworkSummary,
)
from app.services.twin_graph import (
    DEMAND_WINDOW_DAYS,
    NetworkSnapshot,
    build_snapshot,
    overall_risk,
)


class DigitalTwinService:
    def __init__(
        self,
        suppliers: SupplierRepository,
        factories: FactoryRepository,
        warehouses: WarehouseRepository,
        stores: RetailStoreRepository,
        routes: TransportRouteRepository,
        inventory: InventoryRepository,
        sales: SalesRepository,
    ) -> None:
        self.suppliers = suppliers
        self.factories = factories
        self.warehouses = warehouses
        self.stores = stores
        self.routes = routes
        self.inventory = inventory
        self.sales = sales

    async def snapshot(self) -> NetworkSnapshot:
        """Build the shared graph snapshot (also used by the simulator)."""
        rows = await self.sales.store_daily_rows()
        if rows:
            last = max(r[1] for r in rows)
            window_start = last - datetime.timedelta(days=DEMAND_WINDOW_DAYS)
            rows = [r for r in rows if r[1] > window_start]

        return build_snapshot(
            suppliers=await self.suppliers.list_all(),
            factories=await self.factories.list_all(),
            warehouses=await self.warehouses.list_all(),
            stores=await self.stores.list_all(),
            routes=await self.routes.list_all(),
            inventory_by_warehouse=await self.inventory.quantity_by_warehouse(),
            store_daily_rows=rows,
        )

    async def network(self) -> NetworkResponse:
        """Assemble the supply chain network graph for the frontend."""
        snap = await self.snapshot()

        nodes = [
            NetworkNode(
                id=stats.id,
                name=stats.name,
                type=stats.type,
                status=stats.status,
                country=stats.country,
                city=stats.city,
                capacity=int(stats.capacity) if stats.capacity else None,
                current_inventory=(
                    int(stats.inventory_units)
                    if stats.type == NodeType.WAREHOUSE
                    else None
                ),
                utilization_pct=stats.utilization_pct,
                risk_level=stats.risk_level,
            )
            for stats in snap.nodes.values()
        ]
        edges = [
            NetworkEdge(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                transport_mode=edge.transport_mode,
                distance_km=edge.distance_km,
                transit_time_hours=edge.transit_time_hours,
                status=edge.status,
                risk_level=edge.risk_level,
            )
            for edge in snap.edges
        ]

        node_counts: dict[str, int] = {t.value: 0 for t in NodeType}
        for node in nodes:
            node_counts[node.type.value] += 1

        return NetworkResponse(
            nodes=nodes,
            edges=edges,
            summary=NetworkSummary(
                total_nodes=len(nodes),
                total_edges=len(edges),
                node_counts=node_counts,
                overall_risk=overall_risk(list(snap.nodes.values())),
                resilience_score=snap.resilience_score,
            ),
        )
