"""Warehouse CRUD endpoints (responses include utilization)."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, ManagerUser, WarehouseServiceDep
from app.models.enums import EntityStatus
from app.schemas.common import Page
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseRead,
    WarehouseUpdate,
)
from app.utils.pagination import Pagination

router = APIRouter()


@router.get("", response_model=Page[WarehouseRead])
async def list_warehouses(
    _user: CurrentUser,
    service: WarehouseServiceDep,
    params: Pagination,
    status_filter: EntityStatus | None = None,
    search: str | None = None,
) -> Page[WarehouseRead]:
    """List warehouses with live inventory and utilization figures."""
    items, total = await service.list(params, status=status_filter, search=search)
    return Page.build(items, total, params.page, params.size)


@router.post(
    "", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED
)
async def create_warehouse(
    data: WarehouseCreate, _manager: ManagerUser, service: WarehouseServiceDep
) -> WarehouseRead:
    """Create a warehouse (admin / supply chain manager)."""
    return await service.create(data)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(
    warehouse_id: uuid.UUID, _user: CurrentUser, service: WarehouseServiceDep
) -> WarehouseRead:
    """Fetch a single warehouse with utilization."""
    return await service.get(warehouse_id)


@router.put("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    data: WarehouseUpdate,
    _manager: ManagerUser,
    service: WarehouseServiceDep,
) -> WarehouseRead:
    """Update a warehouse (admin / supply chain manager)."""
    return await service.update(warehouse_id, data)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: uuid.UUID,
    _manager: ManagerUser,
    service: WarehouseServiceDep,
) -> None:
    """Delete a warehouse (admin / supply chain manager)."""
    await service.delete(warehouse_id)
