"""Forecast history repository."""

from sqlalchemy.orm import selectinload

from app.models.forecast_history import ForecastHistory
from app.repositories.base import BaseRepository

FORECAST_LOAD_OPTIONS = (
    selectinload(ForecastHistory.product),
    selectinload(ForecastHistory.warehouse),
)


class ForecastRepository(BaseRepository[ForecastHistory]):
    model = ForecastHistory

    async def recent(self, limit: int = 20) -> list[ForecastHistory]:
        items, _ = await self.list(limit=limit, options=FORECAST_LOAD_OPTIONS)
        return items
