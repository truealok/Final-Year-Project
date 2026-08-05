"""Analytics endpoint - trends and performance metrics."""

from fastapi import APIRouter

from app.core.dependencies import AnalyticsServiceDep, CurrentUser
from app.schemas.analytics import AnalyticsResponse

router = APIRouter()


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    _user: CurrentUser, service: AnalyticsServiceDep
) -> AnalyticsResponse:
    """Return all analytics series in one payload.

    Includes demand trend, inventory trend, supplier performance, warehouse
    utilization, disruption frequency, recovery trend and carbon emissions.
    """
    return await service.overview()
