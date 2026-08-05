"""User management endpoints (admin) + self-service profile update."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import AdminUser, CurrentUser, UserServiceDep
from app.schemas.common import Page
from app.schemas.user import UserRead, UserUpdate, UserUpdateMe
from app.utils.pagination import Pagination

router = APIRouter()


@router.get("", response_model=Page[UserRead])
async def list_users(
    _admin: AdminUser, service: UserServiceDep, params: Pagination
) -> Page[UserRead]:
    """List all users (admin only)."""
    items, total = await service.list(params)
    return Page.build(
        [UserRead.model_validate(u) for u in items],
        total,
        params.page,
        params.size,
    )


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdateMe, user: CurrentUser, service: UserServiceDep
) -> UserRead:
    """Update your own profile (name and/or password)."""
    updated = await service.update_me(user, data)
    return UserRead.model_validate(updated)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID, _admin: AdminUser, service: UserServiceDep
) -> UserRead:
    """Fetch a user by id (admin only)."""
    return UserRead.model_validate(await service.get(user_id))


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    _admin: AdminUser,
    service: UserServiceDep,
) -> UserRead:
    """Update a user's role, name or active flag (admin only)."""
    return UserRead.model_validate(await service.update(user_id, data))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, admin: AdminUser, service: UserServiceDep
) -> None:
    """Delete a user (admin only, cannot delete yourself)."""
    await service.delete(user_id, admin)
