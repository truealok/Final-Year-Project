"""Generic async repository with common CRUD operations."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository implementing common persistence operations.

    Subclasses set ``model`` and may add query methods. Repositories only
    ``flush`` - the session dependency commits at the end of the request.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, obj_id: uuid.UUID) -> ModelT | None:
        """Fetch a single row by primary key."""
        return await self.db.get(self.model, obj_id)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        where: Sequence[Any] = (),
        options: Sequence[Any] = (),
        order_by: Any = None,
    ) -> tuple[list[ModelT], int]:
        """Return ``(items, total)`` for a filtered, paginated query."""
        stmt = select(self.model).where(*where)
        for option in options:
            stmt = stmt.options(option)

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())

        count_stmt = select(func.count()).select_from(
            select(self.model.id).where(*where).subquery()
        )
        total = await self.db.scalar(count_stmt) or 0

        result = await self.db.scalars(stmt.offset(offset).limit(limit))
        return list(result.all()), int(total)

    async def list_all(
        self, *, where: Sequence[Any] = (), options: Sequence[Any] = ()
    ) -> list[ModelT]:
        """Return every matching row (use only for bounded tables)."""
        stmt = select(self.model).where(*where)
        for option in options:
            stmt = stmt.options(option)
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def count(self, *, where: Sequence[Any] = ()) -> int:
        stmt = select(func.count()).select_from(
            select(self.model.id).where(*where).subquery()
        )
        return int(await self.db.scalar(stmt) or 0)

    async def create(self, **data: Any) -> ModelT:
        obj = self.model(**data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def refresh(
        self, obj: ModelT, attribute_names: list[str] | None = None
    ) -> ModelT:
        """Reload attributes (including relationships) from the database."""
        await self.db.refresh(obj, attribute_names=attribute_names)
        return obj

    async def update(self, obj: ModelT, **data: Any) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
        await self.db.flush()
