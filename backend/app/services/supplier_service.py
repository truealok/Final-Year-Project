"""Supplier business logic."""

import uuid

from app.models.enums import EntityStatus, RiskLevel
from app.models.supplier import Supplier
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PaginationParams


class SupplierService:
    def __init__(self, suppliers: SupplierRepository) -> None:
        self.suppliers = suppliers

    async def list(
        self,
        params: PaginationParams,
        *,
        country: str | None = None,
        risk_level: RiskLevel | None = None,
        status: EntityStatus | None = None,
        search: str | None = None,
    ) -> tuple[list[Supplier], int]:
        where = []
        if country:
            where.append(Supplier.country.ilike(country))
        if risk_level:
            where.append(Supplier.risk_level == risk_level)
        if status:
            where.append(Supplier.status == status)
        if search:
            where.append(Supplier.name.ilike(f"%{search}%"))
        return await self.suppliers.list(
            offset=params.offset, limit=params.size, where=where
        )

    async def get(self, supplier_id: uuid.UUID) -> Supplier:
        supplier = await self.suppliers.get(supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier not found.")
        return supplier

    async def create(self, data: SupplierCreate) -> Supplier:
        return await self.suppliers.create(**data.model_dump())

    async def update(
        self, supplier_id: uuid.UUID, data: SupplierUpdate
    ) -> Supplier:
        supplier = await self.get(supplier_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.suppliers.update(supplier, **changes)

    async def delete(self, supplier_id: uuid.UUID) -> None:
        supplier = await self.get(supplier_id)
        await self.suppliers.delete(supplier)
