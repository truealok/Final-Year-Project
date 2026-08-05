"""Digital twin business logic.

PLACEHOLDER ENGINE: real graph analytics (NetworkX) is intentionally NOT
implemented. The network is assembled from real database entities (suppliers,
factories, warehouses, stores, transport routes) with simulated status and
risk attributes. A NetworkX-backed engine can replace the risk/resilience
computations later without changing the API contract.
"""

import random
import uuid

from app.models.enums import NodeType, RiskLevel
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.network_repository import (
    FactoryRepository,
    RetailStoreRepository,
    TransportRouteRepository,
)
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.digital_twin import (
    NetworkEdge,
    NetworkNode,
    NetworkResponse,
    NetworkSummary,
)

_RISK_ORDER = [
    RiskLevel.LOW,
    RiskLevel.MEDIUM,
    RiskLevel.HIGH,
    RiskLevel.CRITICAL,
]


class DigitalTwinService:
    def __init__(
        self,
        suppliers: SupplierRepository,
        factories: FactoryRepository,
        warehouses: WarehouseRepository,
        stores: RetailStoreRepository,
        routes: TransportRouteRepository,
        inventory: InventoryRepository,
    ) -> None:
        self.suppliers = suppliers
        self.factories = factories
        self.warehouses = warehouses
        self.stores = stores
        self.routes = routes
        self.inventory = inventory

    @staticmethod
    def _mock_risk(node_id: uuid.UUID) -> RiskLevel:
        """Deterministic pseudo-risk for nodes without an explicit level."""
        rng = random.Random(str(node_id))
        return rng.choices(_RISK_ORDER, weights=[55, 28, 13, 4], k=1)[0]

    async def network(self) -> NetworkResponse:
        """Assemble the supply chain network graph."""
        nodes: list[NetworkNode] = []
        quantities = await self.inventory.quantity_by_warehouse()

        for supplier in await self.suppliers.list_all():
            nodes.append(
                NetworkNode(
                    id=supplier.id,
                    name=supplier.name,
                    type=NodeType.SUPPLIER,
                    status=supplier.status.value,
                    country=supplier.country,
                    city=supplier.city,
                    risk_level=supplier.risk_level,
                )
            )
        for factory in await self.factories.list_all():
            nodes.append(
                NetworkNode(
                    id=factory.id,
                    name=factory.name,
                    type=NodeType.FACTORY,
                    status=factory.status.value,
                    country=factory.country,
                    city=factory.city,
                    capacity=factory.capacity_per_day,
                    risk_level=self._mock_risk(factory.id),
                )
            )
        for warehouse in await self.warehouses.list_all():
            units = quantities.get(warehouse.id, 0)
            utilization = (
                round(units / warehouse.capacity * 100, 1)
                if warehouse.capacity
                else None
            )
            nodes.append(
                NetworkNode(
                    id=warehouse.id,
                    name=warehouse.name,
                    type=NodeType.WAREHOUSE,
                    status=warehouse.status.value,
                    country=warehouse.country,
                    city=warehouse.city,
                    capacity=warehouse.capacity,
                    current_inventory=units,
                    utilization_pct=utilization,
                    risk_level=self._mock_risk(warehouse.id),
                )
            )
        for store in await self.stores.list_all():
            nodes.append(
                NetworkNode(
                    id=store.id,
                    name=store.name,
                    type=NodeType.RETAIL_STORE,
                    status=store.status.value,
                    country=store.country,
                    city=store.city,
                    risk_level=self._mock_risk(store.id),
                )
            )

        node_ids = {node.id for node in nodes}
        edges = [
            NetworkEdge(
                id=route.id,
                source=route.origin_id,
                target=route.destination_id,
                transport_mode=route.transport_mode.value,
                distance_km=route.distance_km,
                transit_time_hours=route.transit_time_hours,
                status=route.status.value,
                risk_level=route.risk_level,
            )
            for route in await self.routes.list_all()
            if route.origin_id in node_ids and route.destination_id in node_ids
        ]

        return NetworkResponse(
            nodes=nodes, edges=edges, summary=self._summarize(nodes, edges)
        )

    @staticmethod
    def _summarize(
        nodes: list[NetworkNode], edges: list[NetworkEdge]
    ) -> NetworkSummary:
        node_counts: dict[str, int] = {t.value: 0 for t in NodeType}
        risk_score_map = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        total_risk = 0
        for node in nodes:
            node_counts[node.type.value] += 1
            total_risk += risk_score_map[node.risk_level]

        avg_risk = total_risk / len(nodes) if nodes else 0.0
        overall = _RISK_ORDER[min(3, round(avg_risk))]
        resilience = round(max(10.0, 95 - avg_risk * 22), 1)

        return NetworkSummary(
            total_nodes=len(nodes),
            total_edges=len(edges),
            node_counts=node_counts,
            overall_risk=overall,
            resilience_score=resilience,
        )
