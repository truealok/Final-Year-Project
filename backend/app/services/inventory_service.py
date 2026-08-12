"""Inventory business logic (CRUD, stock-status derivation, summary)."""

from __future__ import annotations

import uuid

from app.models.category import Category
from app.models.enums import InventoryStatus
from app.models.inventory import Inventory
from app.models.product import Product
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import (
    CategoryRepository,
    ProductRepository,
)
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.inventory import (
    InventoryCreate,
    InventorySummary,
    InventoryUpdate,
)
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import PaginationParams


class InventoryService:
    def __init__(
        self,
        inventory: InventoryRepository,
        products: ProductRepository,
        categories: CategoryRepository,
        warehouses: WarehouseRepository,
    ) -> None:
        self.inventory = inventory
        self.products = products
        self.categories = categories
        self.warehouses = warehouses

    @staticmethod
    def _derive_status(quantity: int, reorder_point: int) -> InventoryStatus:
        if quantity <= 0:
            return InventoryStatus.OUT_OF_STOCK
        if quantity <= reorder_point:
            return InventoryStatus.LOW_STOCK
        return InventoryStatus.IN_STOCK

    async def list(
        self,
        params: PaginationParams,
        *,
        warehouse_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        status: InventoryStatus | None = None,
    ) -> tuple[list[Inventory], int]:
        where = []
        if warehouse_id:
            where.append(Inventory.warehouse_id == warehouse_id)
        if product_id:
            where.append(Inventory.product_id == product_id)
        if status:
            where.append(Inventory.status == status)
        return await self.inventory.list(
            offset=params.offset, limit=params.size, where=where
        )

    async def get(self, inventory_id: uuid.UUID) -> Inventory:
        item = await self.inventory.get(inventory_id)
        if item is None:
            raise NotFoundError("Inventory record not found.")
        return item

    async def create(self, data: InventoryCreate) -> Inventory:
        if await self.products.get(data.product_id) is None:
            raise NotFoundError("Product not found.")
        if await self.warehouses.get(data.warehouse_id) is None:
            raise NotFoundError("Warehouse not found.")
        existing = await self.inventory.get_by_product_warehouse(
            data.product_id, data.warehouse_id
        )
        if existing is not None:
            raise ConflictError(
                "Inventory for this product already exists at this warehouse."
            )
        status = self._derive_status(data.quantity, data.reorder_point)
        item = await self.inventory.create(**data.model_dump(), status=status)
        # Load the relationships needed by the response schema (async ORM
        # forbids implicit lazy loading).
        return await self.inventory.refresh(item, ["product", "warehouse"])

    async def update(
        self, inventory_id: uuid.UUID, data: InventoryUpdate
    ) -> Inventory:
        item = await self.get(inventory_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        quantity = changes.get("quantity", item.quantity)
        reorder_point = changes.get("reorder_point", item.reorder_point)
        changes["status"] = self._derive_status(quantity, reorder_point)
        return await self.inventory.update(item, **changes)

    async def delete(self, inventory_id: uuid.UUID) -> None:
        item = await self.get(inventory_id)
        await self.inventory.delete(item)

    async def summary(self) -> InventorySummary:
        return InventorySummary(**await self.inventory.summary())

    async def list_products(
        self, params: PaginationParams
    ) -> tuple[list[Product], int]:
        return await self.products.list(
            offset=params.offset, limit=params.size, order_by=Product.name
        )

    async def list_categories(self) -> list[Category]:
        return await self.categories.list_all()
