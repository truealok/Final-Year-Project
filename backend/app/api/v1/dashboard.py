"""Dashboard endpoint - aggregated KPIs for the landing view."""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DashboardServiceDep
from app.schemas.dashboard import DashboardResponse

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    _user: CurrentUser, service: DashboardServiceDep
) -> DashboardResponse:
    """Return the executive dashboard snapshot.

    Includes forecast accuracy, resilience score, expected cost, inventory
    snapshot, stockout probability, recovery time, carbon emissions, the
    latest alerts and recent simulations.
    """
    return await service.overview()
