"""Inventory repository."""

import uuid

from sqlalchemy import func, select

from app.models.enums import InventoryStatus
from app.models.inventory import Inventory
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[Inventory]):
    model = Inventory

    async def get_by_product_warehouse(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> Inventory | None:
        stmt = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
        )
        return await self.db.scalar(stmt)

    async def quantity_by_warehouse(self) -> dict[uuid.UUID, int]:
        """Total units currently held, grouped by warehouse."""
        stmt = select(
            Inventory.warehouse_id, func.sum(Inventory.quantity)
        ).group_by(Inventory.warehouse_id)
        result = await self.db.execute(stmt)
        return {row[0]: int(row[1] or 0) for row in result.all()}

    async def summary(self) -> dict[str, float | int]:
        """Aggregate snapshot used by dashboard and inventory summary."""
        totals_stmt = select(
            func.count(Inventory.id),
            func.coalesce(func.sum(Inventory.quantity), 0),
            func.coalesce(func.sum(Inventory.quantity * Inventory.unit_cost), 0.0),
        )
        total_items, total_units, total_value = (
            await self.db.execute(totals_stmt)
        ).one()

        low = await self.count(
            where=[Inventory.status == InventoryStatus.LOW_STOCK]
        )
        out = await self.count(
            where=[Inventory.status == InventoryStatus.OUT_OF_STOCK]
        )
        return {
            "total_items": int(total_items),
            "total_units": int(total_units),
            "total_value": round(float(total_value), 2),
            "low_stock_items": low,
            "out_of_stock_items": out,
        }
