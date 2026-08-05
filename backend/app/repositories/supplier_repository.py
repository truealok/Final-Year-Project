"""Supplier repository."""

from app.models.supplier import Supplier
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    async def top_by_reliability(self, limit: int = 10) -> list[Supplier]:
        from sqlalchemy import select

        stmt = (
            select(Supplier)
            .order_by(Supplier.reliability_score.desc())
            .limit(limit)
        )
        result = await self.db.scalars(stmt)
        return list(result.all())
