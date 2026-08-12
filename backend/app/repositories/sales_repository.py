"""Sales history repository."""

from datetime import date, timedelta

from sqlalchemy import case, func, select

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

    async def product_window_totals(
        self, window_days: int = 30
    ) -> list[tuple[object, float, float]]:
        """Per product: ``(product_id, last-window units, prior-window units)``.

        Real sales aggregates used by the recommendation engine to detect
        demand growth/decline without fabricating a trend.
        """
        last_day = await self.db.scalar(select(func.max(SalesHistory.date)))
        if last_day is None:
            return []
        mid = last_day - timedelta(days=window_days)
        start = last_day - timedelta(days=2 * window_days)
        stmt = (
            select(
                SalesHistory.product_id,
                func.sum(
                    case(
                        (SalesHistory.date > mid, SalesHistory.quantity_sold),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            (SalesHistory.date <= mid)
                            & (SalesHistory.date > start),
                            SalesHistory.quantity_sold,
                        ),
                        else_=0,
                    )
                ),
            )
            .where(SalesHistory.date > start)
            .group_by(SalesHistory.product_id)
        )
        result = await self.db.execute(stmt)
        return [(row[0], float(row[1] or 0), float(row[2] or 0)) for row in result.all()]

    async def store_daily_rows(
        self, since: date | None = None
    ) -> list[tuple[object, date, int, float]]:
        """Aggregated ``(store_id, date, quantity, revenue)`` rows.

        Feeds the digital-twin/simulation demand statistics (per-store daily
        demand mean and variability from the REAL sales history).
        """
        stmt = (
            select(
                SalesHistory.retail_store_id,
                SalesHistory.date,
                func.sum(SalesHistory.quantity_sold),
                func.sum(SalesHistory.revenue),
            )
            .group_by(SalesHistory.retail_store_id, SalesHistory.date)
        )
        if since is not None:
            stmt = stmt.where(SalesHistory.date >= since)
        result = await self.db.execute(stmt)
        return [
            (row[0], row[1], int(row[2]), float(row[3])) for row in result.all()
        ]
