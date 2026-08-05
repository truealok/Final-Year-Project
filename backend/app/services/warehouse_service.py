"""Warehouse business logic (CRUD + utilization enrichment)."""

import uuid

from app.models.enums import EntityStatus
from app.models.warehouse import Warehouse
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PaginationParams


class WarehouseService:
    def __init__(
        self, warehouses: WarehouseRepository, inventory: InventoryRepository
    ) -> None:
        self.warehouses = warehouses
        self.inventory = inventory

    def _to_read(
        self, warehouse: Warehouse, quantities: dict[uuid.UUID, int]
    ) -> WarehouseRead:
        data = WarehouseRead.model_validate(warehouse)
        units = quantities.get(warehouse.id, 0)
        data.current_inventory = units
        if warehouse.capacity > 0:
            data.utilization_pct = round(units / warehouse.capacity * 100, 1)
        return data

    async def list(
        self,
        params: PaginationParams,
        *,
        status: EntityStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[WarehouseRead], int]:
        where = []
        if status:
            where.append(Warehouse.status == status)
        if search:
            where.append(Warehouse.name.ilike(f"%{search}%"))
        items, total = await self.warehouses.list(
            offset=params.offset, limit=params.size, where=where
        )
        quantities = await self.inventory.quantity_by_warehouse()
        return [self._to_read(w, quantities) for w in items], total

    async def get(self, warehouse_id: uuid.UUID) -> WarehouseRead:
        warehouse = await self._get_model(warehouse_id)
        quantities = await self.inventory.quantity_by_warehouse()
        return self._to_read(warehouse, quantities)

    async def _get_model(self, warehouse_id: uuid.UUID) -> Warehouse:
        warehouse = await self.warehouses.get(warehouse_id)
        if warehouse is None:
            raise NotFoundError("Warehouse not found.")
        return warehouse

    async def create(self, data: WarehouseCreate) -> WarehouseRead:
        warehouse = await self.warehouses.create(**data.model_dump())
        return self._to_read(warehouse, {})

    async def update(
        self, warehouse_id: uuid.UUID, data: WarehouseUpdate
    ) -> WarehouseRead:
        warehouse = await self._get_model(warehouse_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        warehouse = await self.warehouses.update(warehouse, **changes)
        quantities = await self.inventory.quantity_by_warehouse()
        return self._to_read(warehouse, quantities)

    async def delete(self, warehouse_id: uuid.UUID) -> None:
        warehouse = await self._get_model(warehouse_id)
        await self.warehouses.delete(warehouse)
