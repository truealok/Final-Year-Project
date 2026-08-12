"""Disruption simulation business logic — real Monte Carlo engine.

``run`` builds the shared network snapshot (same graph the digital twin
shows), hands it to :mod:`app.services.simulation_engine` and persists the
outcome. All metrics — resilience (area under disrupted vs baseline
service-level curves), expected cost (real average unit price), stockout
probability, recovery time, service level, emissions — emerge from the
simulation; none are drawn from a distribution of "plausible numbers".

The engine is CPU-bound pure Python, so it runs in a worker thread.
"""

import uuid
from typing import Any

import anyio.to_thread

from app.models.enums import RiskLevel
from app.models.simulation_history import SimulationHistory
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.simulation import (
    AffectedNode,
    AffectedRoute,
    SimulationResult,
    SimulationRunRequest,
)
from app.services.digital_twin_service import DigitalTwinService
from app.services.simulation_engine import run_simulation
from app.utils.pagination import PaginationParams


class SimulationService:
    def __init__(
        self,
        simulations: SimulationRepository,
        twin: DigitalTwinService,
    ) -> None:
        self.simulations = simulations
        self.twin = twin

    @staticmethod
    def _risk_from_resilience(score: float) -> RiskLevel:
        if score >= 75:
            return RiskLevel.LOW
        if score >= 55:
            return RiskLevel.MEDIUM
        if score >= 35:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    async def run(
        self, request: SimulationRunRequest, user_id: uuid.UUID | None
    ) -> SimulationResult:
        """Execute the Monte Carlo disruption simulation and persist it."""
        snapshot = await self.twin.snapshot()

        outcome = await anyio.to_thread.run_sync(
            lambda: run_simulation(
                snapshot,
                simulation_type=request.simulation_type,
                severity=request.severity,
                duration_days=request.duration_days,
                probability=request.probability,
                target_node_id=request.affected_node_id,
                n_runs=request.monte_carlo_runs,
            )
        )
        risk_level = self._risk_from_resilience(outcome.resilience_score)

        affected_nodes = [AffectedNode(**n) for n in outcome.affected_nodes]
        affected_routes = [AffectedRoute(**r) for r in outcome.affected_routes]

        results: dict[str, Any] = {
            "engine": "monte_carlo_v1",
            "n_runs": outcome.n_runs,
            "event_occurrence_rate": outcome.event_occurrence_rate,
            "service_level": outcome.service_level,
            "baseline_service_level": outcome.baseline_service_level,
            "emissions_tons_co2": outcome.emissions_tons_co2,
            "mean_service_curve": outcome.mean_service_curve,
            "mean_baseline_curve": outcome.mean_baseline_curve,
            "affected_nodes": [n.model_dump(mode="json") for n in affected_nodes],
            "affected_routes": [
                r.model_dump(mode="json") for r in affected_routes
            ],
            "provenance": (
                "demand statistics from the real sales dataset; network "
                "parameters are configured (scripts/seed_network.py)"
            ),
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
            resilience_score=outcome.resilience_score,
            expected_cost=outcome.expected_cost,
            recovery_time_days=outcome.recovery_time_days,
            stockout_probability=outcome.stockout_probability,
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
            service_level=outcome.service_level,
            baseline_service_level=outcome.baseline_service_level,
            emissions_tons_co2=outcome.emissions_tons_co2,
            n_runs=outcome.n_runs,
            created_at=record.created_at,
        )

    async def history(
        self, params: PaginationParams
    ) -> tuple[list[SimulationHistory], int]:
        return await self.simulations.list(
            offset=params.offset, limit=params.size
        )
