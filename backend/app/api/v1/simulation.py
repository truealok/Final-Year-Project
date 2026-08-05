"""Disruption simulation endpoints (mock engine; Monte Carlo plugs in later)."""

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, SimulationServiceDep
from app.models.enums import SimulationType
from app.schemas.common import Page
from app.schemas.simulation import (
    SimulationHistoryRead,
    SimulationResult,
    SimulationRunRequest,
)
from app.utils.pagination import Pagination

router = APIRouter()


@router.post(
    "/run", response_model=SimulationResult, status_code=status.HTTP_201_CREATED
)
async def run_simulation(
    data: SimulationRunRequest,
    user: CurrentUser,
    service: SimulationServiceDep,
) -> SimulationResult:
    """Run a what-if disruption scenario.

    Supported types: supplier_failure, transport_delay, flood, demand_spike,
    warehouse_failure, machine_breakdown.
    """
    return await service.run(data, user.id)


@router.get("/history", response_model=Page[SimulationHistoryRead])
async def history(
    _user: CurrentUser, service: SimulationServiceDep, params: Pagination
) -> Page[SimulationHistoryRead]:
    """List past simulation runs (newest first)."""
    items, total = await service.history(params)
    return Page.build(
        [SimulationHistoryRead.model_validate(s) for s in items],
        total,
        params.page,
        params.size,
    )


@router.get("/types", response_model=list[str])
async def types(_user: CurrentUser) -> list[str]:
    """List supported simulation scenario types (for UI dropdowns)."""
    return [t.value for t in SimulationType]
