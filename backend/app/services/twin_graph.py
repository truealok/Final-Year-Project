"""Shared supply-chain graph engine (NetworkX).

Builds one :class:`NetworkSnapshot` from the database that BOTH the digital
twin and the disruption-simulation engine consume, so the two features always
describe the same network (products/demand are the real dataset; network
entities and their parameters are configured — see ``scripts/seed_network.py``).

Everything here is deterministic and derived:

- per-store demand statistics (mean/std of daily units) come from the REAL
  sales history over a trailing window;
- warehouse demand = sum of the demand of the stores it serves;
- factory load = demand of the warehouses it feeds; supplier load = factories;
- risk levels are computed from data (inventory cover days, utilization,
  supplier reliability) — no random numbers;
- the network resilience score is a documented composite of redundancy,
  inventory coverage, supplier reliability and store connectivity.
"""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import networkx as nx

from app.models.enums import EntityStatus, NodeType, RiskLevel

DEMAND_WINDOW_DAYS = 90

# Emission factors, kg CO2 per tonne-km (standard logistics literature
# magnitudes — CONFIGURED parameters, not observed data).
EMISSION_KG_PER_TONNE_KM = {
    "truck": 0.105,
    "rail": 0.028,
    "ship": 0.011,
    "air": 0.602,
}
# Average shipment payload used to convert route traffic to tonne-km.
SHIPMENT_PAYLOAD_TONNES = 8.0
UNITS_PER_SHIPMENT = 5000


@dataclass
class NodeStats:
    id: uuid.UUID
    name: str
    type: NodeType
    status: str
    country: str | None = None
    city: str | None = None
    capacity: float | None = None          # units (warehouse) / units per day (factory)
    inventory_units: float = 0.0
    daily_demand: float = 0.0              # real, from sales window
    demand_std: float = 0.0
    reliability: float | None = None       # suppliers only, 0-100
    lead_time_days: float | None = None    # suppliers only
    cover_days: float | None = None        # warehouses only
    utilization_pct: float | None = None
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class EdgeStats:
    id: uuid.UUID
    source: uuid.UUID
    target: uuid.UUID
    transport_mode: str
    distance_km: float
    transit_time_hours: float
    cost_per_shipment: float
    status: str
    risk_level: RiskLevel


@dataclass
class NetworkSnapshot:
    nodes: dict[uuid.UUID, NodeStats] = field(default_factory=dict)
    edges: list[EdgeStats] = field(default_factory=list)
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    avg_unit_price: float = 0.0            # real: revenue / units over window
    window_days: int = DEMAND_WINDOW_DAYS
    resilience_score: float = 0.0          # 0-100
    resilience_parts: dict[str, float] = field(default_factory=dict)

    def by_type(self, node_type: NodeType) -> list[NodeStats]:
        return [n for n in self.nodes.values() if n.type == node_type]


# ------------------------------------------------------------------ risk
def _risk_from_cover(cover_days: float | None) -> RiskLevel:
    if cover_days is None:
        return RiskLevel.MEDIUM
    if cover_days >= 21:
        return RiskLevel.LOW
    if cover_days >= 10:
        return RiskLevel.MEDIUM
    if cover_days >= 5:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _risk_from_utilization(utilization_pct: float | None) -> RiskLevel:
    if utilization_pct is None:
        return RiskLevel.MEDIUM
    if utilization_pct < 70:
        return RiskLevel.LOW
    if utilization_pct < 90:
        return RiskLevel.MEDIUM
    if utilization_pct < 100:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def _risk_from_reliability(reliability: float) -> RiskLevel:
    if reliability >= 93:
        return RiskLevel.LOW
    if reliability >= 85:
        return RiskLevel.MEDIUM
    if reliability >= 78:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


_RISK_SCORE = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def overall_risk(nodes: list[NodeStats]) -> RiskLevel:
    if not nodes:
        return RiskLevel.LOW
    avg = sum(_RISK_SCORE[n.risk_level] for n in nodes) / len(nodes)
    for level, score in reversed(list(_RISK_SCORE.items())):
        if avg >= score - 0.5:
            return level
    return RiskLevel.LOW


# ------------------------------------------------------------------ build
def build_snapshot(
    *,
    suppliers: list[Any],
    factories: list[Any],
    warehouses: list[Any],
    stores: list[Any],
    routes: list[Any],
    inventory_by_warehouse: dict[uuid.UUID, int],
    store_daily_rows: list[tuple[uuid.UUID, date, int, float]],
) -> NetworkSnapshot:
    """Assemble the snapshot from ORM rows + real sales aggregates."""
    snap = NetworkSnapshot()

    # ---- real demand statistics per store ---------------------------- #
    per_store: dict[uuid.UUID, list[int]] = {}
    total_units = 0.0
    total_revenue = 0.0
    window_end: date | None = None
    for store_id, day, qty, revenue in store_daily_rows:
        per_store.setdefault(store_id, []).append(qty)
        total_units += qty
        total_revenue += revenue
        if window_end is None or day > window_end:
            window_end = day
    snap.avg_unit_price = (
        round(total_revenue / total_units, 4) if total_units else 0.0
    )

    def demand_stats(store_id: uuid.UUID) -> tuple[float, float]:
        values = per_store.get(store_id, [])
        if not values:
            return 0.0, 0.0
        # mean over the full window: days without sales are zero-demand days
        mean = sum(values) / snap.window_days
        observed_std = statistics.pstdev(values) if len(values) > 1 else 0.0
        return round(mean, 3), round(observed_std, 3)

    # ---- nodes -------------------------------------------------------- #
    store_to_wh: dict[uuid.UUID, uuid.UUID | None] = {}
    for store in stores:
        mean, std = demand_stats(store.id)
        store_to_wh[store.id] = store.warehouse_id
        wh_cover_risk = RiskLevel.MEDIUM  # refined after warehouse pass
        snap.nodes[store.id] = NodeStats(
            id=store.id, name=store.name, type=NodeType.RETAIL_STORE,
            status=store.status.value, country=store.country, city=store.city,
            daily_demand=mean, demand_std=std, risk_level=wh_cover_risk,
        )

    wh_demand: dict[uuid.UUID, float] = {}
    wh_std_sq: dict[uuid.UUID, float] = {}
    for store_id, wh_id in store_to_wh.items():
        if wh_id is None:
            continue
        node = snap.nodes[store_id]
        wh_demand[wh_id] = wh_demand.get(wh_id, 0.0) + node.daily_demand
        wh_std_sq[wh_id] = wh_std_sq.get(wh_id, 0.0) + node.demand_std**2

    for wh in warehouses:
        units = float(inventory_by_warehouse.get(wh.id, 0))
        demand = wh_demand.get(wh.id, 0.0)
        cover = round(units / demand, 1) if demand > 0 else None
        utilization = (
            round(units / wh.capacity * 100, 1) if wh.capacity else None
        )
        snap.nodes[wh.id] = NodeStats(
            id=wh.id, name=wh.name, type=NodeType.WAREHOUSE,
            status=wh.status.value, country=wh.country, city=wh.city,
            capacity=float(wh.capacity or 0), inventory_units=units,
            daily_demand=round(demand, 3),
            demand_std=round(wh_std_sq.get(wh.id, 0.0) ** 0.5, 3),
            cover_days=cover, utilization_pct=utilization,
            risk_level=_risk_from_cover(cover),
        )

    # refine store risk from its serving warehouse's cover
    for store_id, wh_id in store_to_wh.items():
        wh_node = snap.nodes.get(wh_id) if wh_id else None
        snap.nodes[store_id].risk_level = (
            _risk_from_cover(wh_node.cover_days) if wh_node else RiskLevel.MEDIUM
        )

    # factory load = demand of warehouses it feeds (from routes, filled below)
    for factory in factories:
        snap.nodes[factory.id] = NodeStats(
            id=factory.id, name=factory.name, type=NodeType.FACTORY,
            status=factory.status.value, country=factory.country,
            city=factory.city, capacity=float(factory.capacity_per_day or 0),
        )
    for supplier in suppliers:
        reliability = float(supplier.reliability_score or 0)
        snap.nodes[supplier.id] = NodeStats(
            id=supplier.id, name=supplier.name, type=NodeType.SUPPLIER,
            status=supplier.status.value, country=supplier.country,
            city=supplier.city, reliability=reliability,
            lead_time_days=float(supplier.lead_time_days or 0),
            risk_level=_risk_from_reliability(reliability),
        )

    # ---- edges + graph ------------------------------------------------ #
    node_ids = set(snap.nodes)
    for route in routes:
        if route.origin_id not in node_ids or route.destination_id not in node_ids:
            continue
        snap.edges.append(EdgeStats(
            id=route.id, source=route.origin_id, target=route.destination_id,
            transport_mode=route.transport_mode.value,
            distance_km=float(route.distance_km or 0),
            transit_time_hours=float(route.transit_time_hours or 0),
            cost_per_shipment=float(route.cost_per_shipment or 0),
            status=route.status.value, risk_level=route.risk_level,
        ))

    graph = nx.DiGraph()
    for node in snap.nodes.values():
        graph.add_node(node.id, type=node.type.value)
    for edge in snap.edges:
        graph.add_edge(
            edge.source, edge.target,
            lead_time_days=edge.transit_time_hours / 24,
            mode=edge.transport_mode,
            distance_km=edge.distance_km,
            active=edge.status == EntityStatus.ACTIVE.value,
        )
    snap.graph = graph

    # distribute warehouse demand upstream: factory load, then utilization
    for factory in factories:
        fed = [
            t for _, t in graph.out_edges(factory.id)
            if snap.nodes[t].type == NodeType.WAREHOUSE
        ]
        load = sum(
            snap.nodes[wh_id].daily_demand
            / max(1, graph.in_degree(wh_id))  # demand split across feeders
            for wh_id in fed
        )
        node = snap.nodes[factory.id]
        node.daily_demand = round(load, 3)
        node.utilization_pct = (
            round(load / node.capacity * 100, 1) if node.capacity else None
        )
        node.risk_level = _risk_from_utilization(node.utilization_pct)

    # disrupted/inactive entities are always critical
    for node in snap.nodes.values():
        if node.status in (
            EntityStatus.DISRUPTED.value,
            EntityStatus.INACTIVE.value,
        ):
            node.risk_level = RiskLevel.CRITICAL

    # ---- resilience score (documented composite, 0-100) --------------- #
    snap.resilience_score, snap.resilience_parts = _resilience(snap)
    return snap


def _resilience(snap: NetworkSnapshot) -> tuple[float, dict[str, float]]:
    """Composite resilience:

    - redundancy: share of factories/warehouses with >= 2 inbound sources
    - coverage:   mean over warehouses of min(1, cover_days / 21)
    - reliability: mean supplier reliability / 100
    - connectivity: share of stores reachable from at least one supplier
    """
    graph = snap.graph
    mid_nodes = [
        n for n in snap.nodes.values()
        if n.type in (NodeType.FACTORY, NodeType.WAREHOUSE)
    ]
    redundancy = (
        sum(1 for n in mid_nodes if graph.in_degree(n.id) >= 2) / len(mid_nodes)
        if mid_nodes else 0.0
    )

    warehouses = snap.by_type(NodeType.WAREHOUSE)
    covers = [n.cover_days for n in warehouses if n.cover_days is not None]
    coverage = (
        sum(min(1.0, c / 21) for c in covers) / len(covers) if covers else 0.0
    )

    suppliers = snap.by_type(NodeType.SUPPLIER)
    reliability = (
        sum((n.reliability or 0) for n in suppliers) / len(suppliers) / 100
        if suppliers else 0.0
    )

    stores = snap.by_type(NodeType.RETAIL_STORE)
    supplier_ids = [n.id for n in suppliers]
    reachable: set[uuid.UUID] = set()
    for supplier_id in supplier_ids:
        reachable |= nx.descendants(graph, supplier_id)
    connectivity = (
        sum(1 for s in stores if s.id in reachable) / len(stores)
        if stores else 0.0
    )

    parts = {
        "redundancy": round(redundancy, 3),
        "inventory_coverage": round(coverage, 3),
        "supplier_reliability": round(reliability, 3),
        "store_connectivity": round(connectivity, 3),
    }
    score = round(
        100 * (
            0.30 * redundancy
            + 0.30 * coverage
            + 0.25 * reliability
            + 0.15 * connectivity
        ),
        1,
    )
    return score, parts


def route_emissions_kg_per_day(snap: NetworkSnapshot) -> float:
    """Estimated daily transport emissions at current demand levels.

    Traffic on each active edge ≈ the destination node's daily demand
    (units) split across its inbound edges, converted to shipments and
    tonne-km with the configured factors. Deterministic; no randomness.
    """
    total_kg = 0.0
    for edge in snap.edges:
        if edge.status != EntityStatus.ACTIVE.value:
            continue
        dest = snap.nodes.get(edge.target)
        if dest is None or dest.daily_demand <= 0:
            continue
        inbound = max(1, snap.graph.in_degree(edge.target))
        units_per_day = dest.daily_demand / inbound
        shipments_per_day = units_per_day / UNITS_PER_SHIPMENT
        tonne_km = shipments_per_day * SHIPMENT_PAYLOAD_TONNES * edge.distance_km
        factor = EMISSION_KG_PER_TONNE_KM.get(edge.transport_mode, 0.105)
        total_kg += tonne_km * factor
    return round(total_kg, 2)
