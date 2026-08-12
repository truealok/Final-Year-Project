"""Unit tests for the NetworkX twin graph and the Monte Carlo engine.

Pure-python tests over a small fabricated network (dataclass stand-ins for
ORM rows) — no database, fully deterministic.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models.enums import (
    EntityStatus,
    NodeType,
    RiskLevel,
    SeverityLevel,
    SimulationType,
    TransportMode,
)
from app.services.simulation_engine import run_simulation
from app.services.twin_graph import build_snapshot, route_emissions_kg_per_day


@dataclass
class _Row:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = "row"
    country: str = "UK"
    city: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE


@dataclass
class _Supplier(_Row):
    reliability_score: float = 90.0
    lead_time_days: int = 5
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class _Factory(_Row):
    capacity_per_day: int = 10_000


@dataclass
class _Warehouse(_Row):
    capacity: int = 100_000


@dataclass
class _Store(_Row):
    warehouse_id: uuid.UUID | None = None


@dataclass
class _Route:
    origin_id: uuid.UUID
    destination_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    transport_mode: TransportMode = TransportMode.TRUCK
    distance_km: float = 300.0
    transit_time_hours: float = 48.0
    cost_per_shipment: float = 500.0
    status: EntityStatus = EntityStatus.ACTIVE
    risk_level: RiskLevel = RiskLevel.LOW


def _make_snapshot(inventory_units: int = 3000, days: int = 90):
    """supplier -> factory -> warehouse <- store with 100 units/day demand."""
    supplier = _Supplier(name="S1")
    factory = _Factory(name="F1")
    warehouse = _Warehouse(name="W1")
    store = _Store(name="R1", warehouse_id=warehouse.id)
    routes = [
        _Route(origin_id=supplier.id, destination_id=factory.id),
        _Route(origin_id=factory.id, destination_id=warehouse.id),
        _Route(origin_id=warehouse.id, destination_id=store.id),
    ]
    start = date(2026, 1, 1)
    daily_rows = [
        (store.id, start + timedelta(days=i), 100, 500.0) for i in range(days)
    ]
    return build_snapshot(
        suppliers=[supplier],
        factories=[factory],
        warehouses=[warehouse],
        stores=[store],
        routes=routes,
        inventory_by_warehouse={warehouse.id: inventory_units},
        store_daily_rows=daily_rows,
    ), warehouse


# --------------------------------------------------------------------- twin
def test_snapshot_demand_and_cover_derivation():
    snap, warehouse = _make_snapshot(inventory_units=3000)
    wh = snap.nodes[warehouse.id]
    assert wh.daily_demand == 100.0          # 100 units/day, real aggregate
    assert wh.cover_days == 30.0             # 3000 / 100
    assert wh.risk_level == RiskLevel.LOW    # >= 21 days cover
    assert snap.avg_unit_price == 5.0        # 500 revenue / 100 units


def test_snapshot_low_cover_raises_risk():
    snap, warehouse = _make_snapshot(inventory_units=400)  # 4 days cover
    assert snap.nodes[warehouse.id].risk_level == RiskLevel.CRITICAL


def test_resilience_composite_in_bounds():
    snap, _ = _make_snapshot()
    assert 0 <= snap.resilience_score <= 100
    parts = snap.resilience_parts
    assert set(parts) == {
        "redundancy",
        "inventory_coverage",
        "supplier_reliability",
        "store_connectivity",
    }
    assert parts["store_connectivity"] == 1.0  # store reachable from supplier


def test_route_emissions_positive_and_deterministic():
    snap, _ = _make_snapshot()
    kg = route_emissions_kg_per_day(snap)
    assert kg > 0
    assert kg == route_emissions_kg_per_day(snap)


# --------------------------------------------------------------- simulation
def _run(snap, sim_type, severity=SeverityLevel.HIGH, duration=14, prob=1.0):
    return run_simulation(
        snap,
        simulation_type=sim_type,
        severity=severity,
        duration_days=duration,
        probability=prob,
        n_runs=60,
    )


def test_simulation_deterministic():
    snap, _ = _make_snapshot()
    a = _run(snap, SimulationType.DEMAND_SPIKE)
    b = _run(snap, SimulationType.DEMAND_SPIKE)
    assert a.resilience_score == b.resilience_score
    assert a.expected_cost == b.expected_cost


def test_warehouse_failure_reduces_service():
    snap, _ = _make_snapshot()
    outcome = _run(snap, SimulationType.WAREHOUSE_FAILURE,
                   severity=SeverityLevel.CRITICAL)
    assert outcome.resilience_score < 95
    assert outcome.service_level < outcome.baseline_service_level
    assert outcome.expected_cost > 0
    assert outcome.stockout_probability > 0
    assert outcome.affected_nodes  # the failed warehouse is reported


def test_severity_orders_impact():
    snap, _ = _make_snapshot(inventory_units=800)  # lean: 8 days cover
    low = _run(snap, SimulationType.WAREHOUSE_FAILURE, SeverityLevel.LOW)
    critical = _run(
        snap, SimulationType.WAREHOUSE_FAILURE, SeverityLevel.CRITICAL
    )
    assert critical.resilience_score <= low.resilience_score
    assert critical.expected_cost >= low.expected_cost


def test_zero_probability_means_no_impact():
    snap, _ = _make_snapshot()
    outcome = _run(snap, SimulationType.WAREHOUSE_FAILURE, prob=0.0)
    assert outcome.resilience_score == 100.0
    assert outcome.event_occurrence_rate == 0.0


def test_resilience_is_area_ratio_bounded():
    snap, _ = _make_snapshot()
    for sim_type in SimulationType:
        outcome = _run(snap, sim_type, duration=7)
        assert 0 <= outcome.resilience_score <= 100
        assert 0 <= outcome.stockout_probability <= 1
        assert outcome.recovery_time_days >= 0
        assert outcome.emissions_tons_co2 >= 0
        assert len(outcome.mean_service_curve) > 0


def test_empty_network_degenerate_but_honest():
    snap = build_snapshot(
        suppliers=[], factories=[], warehouses=[], stores=[], routes=[],
        inventory_by_warehouse={}, store_daily_rows=[],
    )
    outcome = _run(snap, SimulationType.SUPPLIER_FAILURE)
    assert outcome.resilience_score == 100.0
    assert outcome.expected_cost == 0.0
    assert outcome.affected_nodes == []
