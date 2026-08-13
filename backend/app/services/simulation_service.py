"""Disruption simulation business logic.

PLACEHOLDER ENGINE: a real Monte Carlo simulation is intentionally NOT
implemented. ``_compute_outcome`` derives plausible outcome metrics from the
scenario inputs. Swap it for the real engine later - the API contract
(routes, request and response schemas) will not change.
"""

import random
import uuid
from typing import Any

from app.models.enums import NodeType, RiskLevel, SeverityLevel
from app.models.simulation_history import SimulationHistory
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.simulation import (
    AffectedNode,
    AffectedRoute,
    SimulationResult,
    SimulationRunRequest,
)
from app.utils.pagination import PaginationParams

_SEVERITY_WEIGHTS = {
    SeverityLevel.LOW: 0.25,
    SeverityLevel.MEDIUM: 0.45,
    SeverityLevel.HIGH: 0.70,
    SeverityLevel.CRITICAL: 0.90,
}

_FALLBACK_NODES = [
    ("Shenzhen Components Ltd", NodeType.SUPPLIER),
    ("Rotterdam Distribution Hub", NodeType.WAREHOUSE),
    ("Plant Stuttgart", NodeType.FACTORY),
    ("Chicago Regional DC", NodeType.WAREHOUSE),
]

_ROUTE_MODES = ["truck", "rail", "ship", "air"]


class SimulationService:
    def __init__(
        self,
        simulations: SimulationRepository,
        suppliers: SupplierRepository,
        warehouses: WarehouseRepository,
    ) -> None:
        self.simulations = simulations
        self.suppliers = suppliers
        self.warehouses = warehouses

    @staticmethod
    def _risk_from_resilience(score: float) -> RiskLevel:
        if score >= 75:
            return RiskLevel.LOW
        if score >= 55:
            return RiskLevel.MEDIUM
        if score >= 35:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    def _compute_outcome(
        self, request: SimulationRunRequest, rng: random.Random
    ) -> dict[str, float]:
        """Derive plausible outcome metrics from the scenario inputs."""
        weight = _SEVERITY_WEIGHTS[request.severity]
        prob = request.probability
        duration = request.duration_days

        resilience = 100 - weight * 100 * (0.55 + 0.45 * prob)
        resilience -= min(duration, 60) * 0.35
        resilience += rng.uniform(-3, 3)
        resilience = round(max(5.0, min(98.0, resilience)), 1)

        expected_cost = (
            (25_000 + 400_000 * weight)
            * (0.5 + prob)
            * (1 + duration / 30)
            * rng.uniform(0.9, 1.1)
        )
        recovery = duration * (0.5 + weight * 1.4) * rng.uniform(0.85, 1.15)
        stockout = min(0.99, weight * (0.35 + 0.65 * prob) * (1 + duration / 60))

        return {
            "resilience_score": resilience,
            "expected_cost": round(expected_cost, 2),
            "recovery_time_days": round(recovery, 1),
            "stockout_probability": round(stockout, 3),
        }

    async def _pick_affected_nodes(
        self, request: SimulationRunRequest, rng: random.Random
    ) -> list[AffectedNode]:
        """Choose impacted nodes, preferring real records from the database."""
        nodes: list[AffectedNode] = []
        suppliers, _ = await self.suppliers.list(limit=10)
        warehouses, _ = await self.warehouses.list(limit=10)

        pool: list[tuple[uuid.UUID | None, str, str]] = [
            (s.id, s.name, NodeType.SUPPLIER.value) for s in suppliers
        ] + [(w.id, w.name, NodeType.WAREHOUSE.value) for w in warehouses]
        if not pool:
            pool = [(None, name, t.value) for name, t in _FALLBACK_NODES]

        count = min(len(pool), rng.randint(2, 4))
        for node_id, name, node_type in rng.sample(pool, k=count):
            nodes.append(
                AffectedNode(
                    id=node_id,
                    name=name,
                    type=node_type,
                    impact_pct=round(rng.uniform(15, 85), 1),
                )
            )

        # The explicitly targeted node is always first and hit hardest.
        if request.affected_node_id is not None:
            nodes.insert(
                0,
                AffectedNode(
                    id=request.affected_node_id,
                    name="Targeted node",
                    type=(
                        request.affected_node_type.value
                        if request.affected_node_type
                        else "unknown"
                    ),
                    impact_pct=round(rng.uniform(70, 95), 1),
                ),
            )
        return nodes

    @staticmethod
    def _mock_routes(rng: random.Random) -> list[AffectedRoute]:
        routes = []
        for i in range(rng.randint(1, 3)):
            routes.append(
                AffectedRoute(
                    name=f"Route R-{rng.randint(100, 999)}",
                    transport_mode=rng.choice(_ROUTE_MODES),
                    delay_hours=round(rng.uniform(6, 96), 1),
                    status=rng.choice(["delayed", "rerouted", "suspended"]),
                )
            )
        return routes

    async def run(
        self, request: SimulationRunRequest, user_id: uuid.UUID | None
    ) -> SimulationResult:
        """Execute a (mock) disruption simulation and persist the outcome."""
        rng = random.Random(
            f"{request.simulation_type.value}:{request.severity.value}:"
            f"{request.duration_days}:{request.probability}:"
            f"{request.affected_node_id}"
        )
        outcome = self._compute_outcome(request, rng)
        risk_level = self._risk_from_resilience(outcome["resilience_score"])
        affected_nodes = await self._pick_affected_nodes(request, rng)
        affected_routes = self._mock_routes(rng)

        results: dict[str, Any] = {
            "affected_nodes": [n.model_dump(mode="json") for n in affected_nodes],
            "affected_routes": [r.model_dump(mode="json") for r in affected_routes],
            "engine": "mock_engine_v1",
        }
        record = await self.simulations.create(
            simulation_type=request.simulation_type,
            severity=request.severity,
            duration_days=request.duration_days,
            probability=request.probability,
            affected_node_id=request.affected_node_id,
            affected_node_type=(
                request.affected_node_type.value
                if request.affected_node_type
                else None
            ),
            parameters=request.model_dump(mode="json"),
            **outcome,
            risk_level=risk_level,
            results=results,
            created_by=user_id,
        )
        return SimulationResult(
            simulation_id=record.id,
            simulation_type=record.simulation_type,
            severity=record.severity,
            duration_days=record.duration_days,
            probability=record.probability,
            resilience_score=record.resilience_score,
            expected_cost=record.expected_cost,
            recovery_time_days=record.recovery_time_days,
            stockout_probability=record.stockout_probability,
            risk_level=record.risk_level,
            affected_nodes=affected_nodes,
            affected_routes=affected_routes,
            created_at=record.created_at,
        )

    async def history(
        self, params: PaginationParams
    ) -> tuple[list[SimulationHistory], int]:
        return await self.simulations.list(
            offset=params.offset, limit=params.size
        )
