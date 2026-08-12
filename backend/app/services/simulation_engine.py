"""Monte Carlo disruption-simulation engine.

Pure, deterministic (seeded) engine over the shared
:class:`~app.services.twin_graph.NetworkSnapshot`. Nothing here is a random
KPI: every metric emerges from an explicit day-by-day inventory/service
simulation.

Model (documented simplifications)
----------------------------------
Each warehouse runs a daily loop::

    demand_d   ~ Normal(mean, std)  truncated at 0    (REAL demand stats)
    inflow_d   = expected demand x upstream availability, arriving after the
                 inbound lead time (pipeline), reduced/delayed by disruptions
    fulfilled_d = min(demand_d, inventory + inflow_d, throughput cap)
    inventory  -> inventory + inflow_d - fulfilled_d

Upstream availability propagates supplier -> factory -> warehouse along the
graph: a failed supplier reduces its factories' input in proportion to the
factory's supplier count; a reduced factory cuts inflow of the warehouses it
feeds in proportion to their feeder count. Transport delays shift pipeline
arrivals. Warehouse disruptions cap throughput. Demand spikes scale demand.

Per replication the **service-level curve** (fulfilled/demand per day) is
compared with a baseline run using the *same* demand draws and no disruption:

    resilience = area(disrupted curve) / area(baseline curve)   in [0, 1]

The final score is the mean across replications (x100 for the API contract).
Each replication samples whether the event occurs at all (``probability``),
so all reported values are expected values over occurrence.

Costs use the REAL average unit price from the sales window (lost sales +
a configured 15% expediting surcharge on recovered backlog). Emissions use
the configured per-mode factors from :mod:`app.services.twin_graph`.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field

from app.models.enums import NodeType, SeverityLevel, SimulationType
from app.services.twin_graph import (
    EMISSION_KG_PER_TONNE_KM,
    SHIPMENT_PAYLOAD_TONNES,
    UNITS_PER_SHIPMENT,
    NetworkSnapshot,
    route_emissions_kg_per_day,
)

SEVERITY_WEIGHTS = {
    SeverityLevel.LOW: 0.25,
    SeverityLevel.MEDIUM: 0.45,
    SeverityLevel.HIGH: 0.70,
    SeverityLevel.CRITICAL: 0.90,
}

EXPEDITE_SURCHARGE = 0.15          # of unit price, on backlog recovered late
RECOVERY_THRESHOLD = 0.98          # service back to >=98% of baseline
DEMAND_SPIKE_MAX = 1.0             # +100% at severity weight 1.0
TRANSPORT_DELAY_MAX_DAYS = 7.0     # extra lead time at severity weight 1.0


@dataclass
class ScenarioOutcome:
    resilience_score: float        # 0-100
    expected_cost: float
    recovery_time_days: float
    stockout_probability: float
    service_level: float           # 0-1 mean over disrupted runs
    baseline_service_level: float
    emissions_tons_co2: float
    n_runs: int
    event_occurrence_rate: float
    affected_nodes: list[dict] = field(default_factory=list)
    affected_routes: list[dict] = field(default_factory=list)
    mean_service_curve: list[float] = field(default_factory=list)
    mean_baseline_curve: list[float] = field(default_factory=list)


@dataclass
class _WarehouseModel:
    node_id: uuid.UUID
    name: str
    demand_mean: float
    demand_std: float
    inventory0: float
    capacity: float
    lead_time_days: float          # mean inbound lead time (factory legs)
    feeder_factories: list[uuid.UUID] = field(default_factory=list)


def _mean_inbound_lead(snap: NetworkSnapshot, wh_id: uuid.UUID) -> float:
    leads = [
        data["lead_time_days"]
        for _, _, data in snap.graph.in_edges(wh_id, data=True)
    ]
    return sum(leads) / len(leads) if leads else 3.0


def _build_models(snap: NetworkSnapshot) -> list[_WarehouseModel]:
    models = []
    for node in snap.by_type(NodeType.WAREHOUSE):
        if node.daily_demand <= 0:
            continue
        feeders = [
            source
            for source, _ in snap.graph.in_edges(node.id)
            if snap.nodes[source].type == NodeType.FACTORY
        ]
        std = node.demand_std if node.demand_std > 0 else node.daily_demand * 0.1
        models.append(_WarehouseModel(
            node_id=node.id,
            name=node.name,
            demand_mean=node.daily_demand,
            demand_std=std,
            inventory0=node.inventory_units,
            capacity=node.capacity or math.inf,
            lead_time_days=_mean_inbound_lead(snap, node.id),
            feeder_factories=feeders,
        ))
    return models


def _downstream_demand(snap: NetworkSnapshot, node_id: uuid.UUID) -> float:
    """Total warehouse daily demand reachable from *node_id* in the graph."""
    import networkx as nx

    reachable = nx.descendants(snap.graph, node_id) | {node_id}
    return sum(
        snap.nodes[n].daily_demand
        for n in reachable
        if snap.nodes[n].type == NodeType.WAREHOUSE
    )


def _pick_target(
    snap: NetworkSnapshot,
    sim_type: SimulationType,
    requested: uuid.UUID | None,
) -> uuid.UUID | None:
    """Requested node, else the node of the relevant type with the largest
    downstream demand (the honest 'worst reasonable case' default)."""
    if requested is not None and requested in snap.nodes:
        return requested
    type_for = {
        SimulationType.SUPPLIER_FAILURE: NodeType.SUPPLIER,
        SimulationType.MACHINE_BREAKDOWN: NodeType.FACTORY,
        SimulationType.WAREHOUSE_FAILURE: NodeType.WAREHOUSE,
        SimulationType.FLOOD: NodeType.WAREHOUSE,
        SimulationType.TRANSPORT_DELAY: NodeType.WAREHOUSE,
        SimulationType.DEMAND_SPIKE: NodeType.WAREHOUSE,
    }[sim_type]
    candidates = snap.by_type(type_for)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda n: (_downstream_demand(snap, n.id), str(n.id)),
    ).id


def _factory_availability(
    snap: NetworkSnapshot,
    factory_id: uuid.UUID,
    failed_supplier: uuid.UUID | None,
    supplier_loss: float,
    factory_loss: dict[uuid.UUID, float],
) -> float:
    """Input-side availability of a factory in [0, 1]."""
    availability = 1.0 - factory_loss.get(factory_id, 0.0)
    if failed_supplier is not None:
        supplier_ids = [
            s for s, _ in snap.graph.in_edges(factory_id)
            if snap.nodes[s].type == NodeType.SUPPLIER
        ]
        if failed_supplier in supplier_ids and supplier_ids:
            availability *= 1.0 - supplier_loss / len(supplier_ids)
    return max(0.0, availability)


def run_simulation(
    snap: NetworkSnapshot,
    *,
    simulation_type: SimulationType,
    severity: SeverityLevel,
    duration_days: int,
    probability: float,
    target_node_id: uuid.UUID | None = None,
    n_runs: int = 500,
    seed: str = "",
) -> ScenarioOutcome:
    """Run the Monte Carlo simulation; deterministic for identical inputs."""
    weight = SEVERITY_WEIGHTS[severity]
    models = _build_models(snap)
    target = _pick_target(snap, simulation_type, target_node_id)

    horizon = int(
        duration_days
        + max((m.lead_time_days for m in models), default=3.0) * 2
        + 14
    )
    rng = random.Random(
        f"{seed}:{simulation_type.value}:{severity.value}:{duration_days}:"
        f"{probability}:{target}:{n_runs}"
    )

    if not models:
        # No demand-bearing warehouses (e.g. empty dev database): report a
        # degenerate but honest outcome instead of fabricating one.
        return ScenarioOutcome(
            resilience_score=100.0, expected_cost=0.0, recovery_time_days=0.0,
            stockout_probability=0.0, service_level=1.0,
            baseline_service_level=1.0, emissions_tons_co2=0.0,
            n_runs=n_runs, event_occurrence_rate=0.0,
        )

    # --- per-scenario knobs ------------------------------------------- #
    failed_supplier = target if simulation_type == SimulationType.SUPPLIER_FAILURE else None
    factory_loss: dict[uuid.UUID, float] = (
        {target: weight}
        if simulation_type == SimulationType.MACHINE_BREAKDOWN and target
        else {}
    )
    wh_throughput_loss: dict[uuid.UUID, float] = {}
    extra_lead_days = 0.0
    demand_multiplier = 1.0
    if simulation_type in (SimulationType.WAREHOUSE_FAILURE, SimulationType.FLOOD):
        if target:
            wh_throughput_loss[target] = weight
        if simulation_type == SimulationType.FLOOD:
            extra_lead_days = TRANSPORT_DELAY_MAX_DAYS * weight * 0.5
    elif simulation_type == SimulationType.TRANSPORT_DELAY:
        extra_lead_days = TRANSPORT_DELAY_MAX_DAYS * weight
    elif simulation_type == SimulationType.DEMAND_SPIKE:
        demand_multiplier = 1.0 + DEMAND_SPIKE_MAX * weight

    # --- Monte Carlo --------------------------------------------------- #
    resiliences: list[float] = []
    costs: list[float] = []
    recoveries: list[float] = []
    stockout_runs = 0
    occurred_runs = 0
    service_sums: list[float] = []
    baseline_sums: list[float] = []
    curve_acc = [0.0] * horizon
    base_curve_acc = [0.0] * horizon
    node_unmet: dict[uuid.UUID, float] = {m.node_id: 0.0 for m in models}
    node_demand: dict[uuid.UUID, float] = {m.node_id: 0.0 for m in models}
    total_expedited_units = 0.0

    for _ in range(n_runs):
        occurs = rng.random() < probability
        if occurs:
            occurred_runs += 1

        # same demand draws for baseline and disrupted run (paired sample)
        demand_draws = [
            [max(0.0, rng.gauss(m.demand_mean, m.demand_std)) for m in models]
            for _ in range(horizon)
        ]

        def simulate(disrupted: bool):
            inventory = {m.node_id: m.inventory0 for m in models}
            inv0_total = sum(m.inventory0 for m in models) or 1.0
            inv_ratio_curve: list[float] = []
            # pipeline[day][wh] = units arriving that day
            pipeline: list[dict[uuid.UUID, float]] = [
                {} for _ in range(horizon + 40)
            ]
            curve: list[float] = []
            unmet_total = 0.0
            served_total = 0.0
            demand_total = 0.0

            for day in range(horizon):
                in_window = disrupted and occurs and day < duration_days
                day_served = 0.0
                day_demand = 0.0
                for index, model in enumerate(models):
                    demand = demand_draws[day][index]
                    if in_window and simulation_type == SimulationType.DEMAND_SPIKE:
                        demand *= demand_multiplier

                    inflow = pipeline[day].get(model.node_id, 0.0)
                    throughput = math.inf
                    loss = wh_throughput_loss.get(model.node_id)
                    if in_window and loss:
                        # a disrupted warehouse can neither ship nor receive
                        # at full rate; undelivered inbound stock is lost to
                        # this site (rerouted/returned upstream)
                        throughput = model.demand_mean * (1.0 - loss)
                        inflow *= 1.0 - loss
                    stock = inventory[model.node_id] + inflow

                    fulfilled = min(demand, stock, throughput)
                    inventory[model.node_id] = stock - fulfilled

                    # Base-stock replenishment: reorder what was consumed
                    # plus a catch-up term that rebuilds the inventory
                    # position over ~2 weeks after a drawdown. Upstream
                    # availability scales what the factories can actually
                    # ship; the order arrives after the (possibly delayed)
                    # inbound lead time.
                    availability = 1.0
                    if in_window and model.feeder_factories:
                        avail = [
                            _factory_availability(
                                snap, f, failed_supplier,
                                weight, factory_loss,
                            )
                            for f in model.feeder_factories
                        ]
                        availability = sum(avail) / len(avail)
                    catch_up = max(
                        0.0, (model.inventory0 - inventory[model.node_id]) / 14
                    )
                    order = (fulfilled + catch_up) * availability
                    lead = model.lead_time_days + (
                        extra_lead_days if in_window else 0.0
                    )
                    arrive = day + max(1, round(lead))
                    if arrive < len(pipeline):
                        pipeline[arrive][model.node_id] = (
                            pipeline[arrive].get(model.node_id, 0.0) + order
                        )

                    day_served += fulfilled
                    day_demand += demand
                    if disrupted:
                        node_demand[model.node_id] += demand
                        node_unmet[model.node_id] += demand - fulfilled

                curve.append(day_served / day_demand if day_demand else 1.0)
                inv_ratio_curve.append(sum(inventory.values()) / inv0_total)
                unmet_total += day_demand - day_served
                served_total += day_served
                demand_total += day_demand
            service = served_total / demand_total if demand_total else 1.0
            return curve, unmet_total, service, demand_total, inv_ratio_curve

        base_curve, base_unmet, base_service, base_demand, base_inv = simulate(
            disrupted=False
        )
        dis_curve, dis_unmet, dis_service, _, dis_inv = simulate(disrupted=True)

        base_area = sum(base_curve)
        dis_area = sum(dis_curve)
        resilience = min(1.0, dis_area / base_area) if base_area else 1.0
        resiliences.append(resilience)

        extra_unmet = max(0.0, dis_unmet - base_unmet)
        lost_revenue = extra_unmet * snap.avg_unit_price
        expedite = extra_unmet * snap.avg_unit_price * EXPEDITE_SURCHARGE
        costs.append(lost_revenue + expedite)
        total_expedited_units += extra_unmet

        # a stockout event = material unmet demand (> 1% of the period)
        if base_demand and extra_unmet > 0.01 * base_demand:
            stockout_runs += 1

        # recovery: first day after the event where BOTH service and the
        # inventory position are back to (near) baseline — supply flow can
        # resume before buffers are rebuilt, and "recovered" means both.
        recovery = 0.0
        if occurs:
            recovery = float(horizon - duration_days)
            for day in range(duration_days, horizon):
                service_ok = (
                    base_curve[day] == 0
                    or dis_curve[day] / base_curve[day] >= RECOVERY_THRESHOLD
                )
                inventory_ok = (
                    base_inv[day] == 0
                    or dis_inv[day] / base_inv[day] >= 0.90
                )
                if service_ok and inventory_ok:
                    recovery = float(day - duration_days)
                    break
        recoveries.append(recovery)

        service_sums.append(dis_service)
        baseline_sums.append(base_service)
        for day in range(horizon):
            curve_acc[day] += dis_curve[day]
            base_curve_acc[day] += base_curve[day]

    # --- emissions ------------------------------------------------------ #
    baseline_kg_day = route_emissions_kg_per_day(snap)
    expedite_units_per_run = total_expedited_units / n_runs
    # recovered backlog is assumed expedited by air over a mean leg
    active_edges = [e for e in snap.edges if e.distance_km > 0]
    mean_distance = (
        sum(e.distance_km for e in active_edges) / len(active_edges)
        if active_edges else 500.0
    )
    expedite_kg = (
        expedite_units_per_run / UNITS_PER_SHIPMENT
        * SHIPMENT_PAYLOAD_TONNES * mean_distance
        * EMISSION_KG_PER_TONNE_KM["air"]
    )
    emissions_tons = (baseline_kg_day * horizon + expedite_kg) / 1000

    # --- affected nodes/routes ----------------------------------------- #
    affected_nodes = []
    for model in models:
        demand = node_demand[model.node_id]
        if demand <= 0:
            continue
        impact = node_unmet[model.node_id] / demand * 100
        if impact >= 0.5:
            affected_nodes.append({
                "id": str(model.node_id),
                "name": model.name,
                "type": NodeType.WAREHOUSE.value,
                "impact_pct": round(impact, 1),
            })
    affected_nodes.sort(key=lambda n: -n["impact_pct"])
    if target is not None and str(target) not in {n["id"] for n in affected_nodes}:
        target_node = snap.nodes[target]
        affected_nodes.insert(0, {
            "id": str(target),
            "name": target_node.name,
            "type": target_node.type.value,
            "impact_pct": round(weight * 100, 1),
        })

    affected_routes = []
    if occurred_runs and (extra_lead_days > 0 or failed_supplier or factory_loss):
        for edge in snap.edges:
            touched = (
                edge.source == target
                or edge.target == target
                or (extra_lead_days > 0 and simulation_type in (
                    SimulationType.TRANSPORT_DELAY, SimulationType.FLOOD,
                ))
            )
            if touched:
                affected_routes.append({
                    "name": (
                        f"{snap.nodes[edge.source].name} → "
                        f"{snap.nodes[edge.target].name}"
                    ),
                    "transport_mode": edge.transport_mode,
                    "delay_hours": round(extra_lead_days * 24, 1)
                    if extra_lead_days else round(weight * 48, 1),
                    "status": "delayed" if extra_lead_days else "constrained",
                })
        affected_routes = affected_routes[:8]

    downsample = max(1, horizon // 30)
    return ScenarioOutcome(
        resilience_score=round(
            sum(resiliences) / n_runs * 100, 1
        ),
        expected_cost=round(sum(costs) / n_runs, 2),
        recovery_time_days=round(
            sum(recoveries) / max(1, occurred_runs), 1
        ) if occurred_runs else 0.0,
        stockout_probability=round(stockout_runs / n_runs, 3),
        service_level=round(sum(service_sums) / n_runs, 4),
        baseline_service_level=round(sum(baseline_sums) / n_runs, 4),
        emissions_tons_co2=round(emissions_tons, 2),
        n_runs=n_runs,
        event_occurrence_rate=round(occurred_runs / n_runs, 3),
        affected_nodes=affected_nodes[:10],
        affected_routes=affected_routes,
        mean_service_curve=[
            round(curve_acc[d] / n_runs, 4)
            for d in range(0, horizon, downsample)
        ],
        mean_baseline_curve=[
            round(base_curve_acc[d] / n_runs, 4)
            for d in range(0, horizon, downsample)
        ],
    )
