"""Sales history repository."""

from datetime import date

from sqlalchemy import select

from app.models.sales_history import SalesHistory
from app.repositories.base import BaseRepository


class SalesRepository(BaseRepository[SalesHistory]):
    model = SalesHistory

    async def daily_totals(
        self, since: date | None = None
    ) -> list[tuple[date, int, float]]:
        """Return raw ``(date, quantity, revenue)`` rows for aggregation."""
        stmt = select(
            SalesHistory.date,
            SalesHistory.quantity_sold,
            SalesHistory.revenue,
        )
        if since is not None:
            stmt = stmt.where(SalesHistory.date >= since)
        result = await self.db.execute(stmt)
        return [(row[0], int(row[1]), float(row[2])) for row in result.all()]
