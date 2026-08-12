"""User management business logic (admin operations + self-service)."""

from __future__ import annotations

import uuid

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate, UserUpdateMe
from app.utils.exceptions import BadRequestError, NotFoundError
from app.utils.pagination import PaginationParams


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def list(self, params: PaginationParams) -> tuple[list[User], int]:
        return await self.users.list(offset=params.offset, limit=params.size)

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def update(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get(user_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.users.update(user, **changes)

    async def update_me(self, user: User, data: UserUpdateMe) -> User:
        changes: dict = {}
        if data.full_name is not None:
            changes["full_name"] = data.full_name
        if data.password is not None:
            changes["hashed_password"] = hash_password(data.password)
        if changes:
            user = await self.users.update(user, **changes)
        return user

    async def delete(self, user_id: uuid.UUID, current_user: User) -> None:
        if user_id == current_user.id:
            raise BadRequestError("You cannot delete your own account.")
        user = await self.get(user_id)
        await self.users.delete(user)
