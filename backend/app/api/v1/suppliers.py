"""Supplier CRUD endpoints."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, ManagerUser, SupplierServiceDep
from app.models.enums import EntityStatus, RiskLevel
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.utils.pagination import Pagination

router = APIRouter()


@router.get("", response_model=Page[SupplierRead])
async def list_suppliers(
    _user: CurrentUser,
    service: SupplierServiceDep,
    params: Pagination,
    country: str | None = None,
    risk_level: RiskLevel | None = None,
    status_filter: EntityStatus | None = None,
    search: str | None = None,
) -> Page[SupplierRead]:
    """List suppliers with optional country/risk/status/name filters."""
    items, total = await service.list(
        params,
        country=country,
        risk_level=risk_level,
        status=status_filter,
        search=search,
    )
    return Page.build(
        [SupplierRead.model_validate(s) for s in items],
        total,
        params.page,
        params.size,
    )


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate, _manager: ManagerUser, service: SupplierServiceDep
) -> SupplierRead:
    """Create a supplier (admin / supply chain manager)."""
    return SupplierRead.model_validate(await service.create(data))


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: uuid.UUID, _user: CurrentUser, service: SupplierServiceDep
) -> SupplierRead:
    """Fetch a single supplier."""
    return SupplierRead.model_validate(await service.get(supplier_id))


@router.put("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: uuid.UUID,
    data: SupplierUpdate,
    _manager: ManagerUser,
    service: SupplierServiceDep,
) -> SupplierRead:
    """Update a supplier (admin / supply chain manager)."""
    return SupplierRead.model_validate(await service.update(supplier_id, data))


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: uuid.UUID,
    _manager: ManagerUser,
    service: SupplierServiceDep,
) -> None:
    """Delete a supplier (admin / supply chain manager)."""
    await service.delete(supplier_id)
