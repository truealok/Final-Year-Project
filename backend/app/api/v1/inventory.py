"""Inventory CRUD endpoints (+ product/category lookups for UI dropdowns)."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import (
    CurrentUser,
    InventoryServiceDep,
    ManagerUser,
)
from app.models.enums import InventoryStatus
from app.schemas.common import Page
from app.schemas.inventory import (
    InventoryCreate,
    InventoryRead,
    InventorySummary,
    InventoryUpdate,
)
from app.schemas.product import CategoryRead, ProductRead
from app.utils.pagination import Pagination

router = APIRouter()


# Static paths must be declared before the dynamic /{inventory_id} route.
@router.get("/summary", response_model=InventorySummary)
async def summary(
    _user: CurrentUser, service: InventoryServiceDep
) -> InventorySummary:
    """Aggregate inventory snapshot (units, value, low/out-of-stock counts)."""
    return await service.summary()


@router.get("/products", response_model=Page[ProductRead])
async def list_products(
    _user: CurrentUser, service: InventoryServiceDep, params: Pagination
) -> Page[ProductRead]:
    """List products (reference data for inventory management)."""
    items, total = await service.list_products(params)
    return Page.build(
        [ProductRead.model_validate(p) for p in items],
        total,
        params.page,
        params.size,
    )


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(
    _user: CurrentUser, service: InventoryServiceDep
) -> list[CategoryRead]:
    """List product categories."""
    return [
        CategoryRead.model_validate(c) for c in await service.list_categories()
    ]


@router.get("", response_model=Page[InventoryRead])
async def list_inventory(
    _user: CurrentUser,
    service: InventoryServiceDep,
    params: Pagination,
    warehouse_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    status_filter: InventoryStatus | None = None,
) -> Page[InventoryRead]:
    """List inventory records with optional filters."""
    items, total = await service.list(
        params,
        warehouse_id=warehouse_id,
        product_id=product_id,
        status=status_filter,
    )
    return Page.build(
        [InventoryRead.model_validate(i) for i in items],
        total,
        params.page,
        params.size,
    )


@router.post(
    "", response_model=InventoryRead, status_code=status.HTTP_201_CREATED
)
async def create_inventory(
    data: InventoryCreate, _manager: ManagerUser, service: InventoryServiceDep
) -> InventoryRead:
    """Create an inventory record (admin / supply chain manager)."""
    return InventoryRead.model_validate(await service.create(data))


@router.get("/{inventory_id}", response_model=InventoryRead)
async def get_inventory(
    inventory_id: uuid.UUID, _user: CurrentUser, service: InventoryServiceDep
) -> InventoryRead:
    """Fetch a single inventory record."""
    return InventoryRead.model_validate(await service.get(inventory_id))


@router.put("/{inventory_id}", response_model=InventoryRead)
async def update_inventory(
    inventory_id: uuid.UUID,
    data: InventoryUpdate,
    _manager: ManagerUser,
    service: InventoryServiceDep,
) -> InventoryRead:
    """Update an inventory record (admin / supply chain manager)."""
    return InventoryRead.model_validate(await service.update(inventory_id, data))


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory(
    inventory_id: uuid.UUID,
    _manager: ManagerUser,
    service: InventoryServiceDep,
) -> None:
    """Delete an inventory record (admin / supply chain manager)."""
    await service.delete(inventory_id)
