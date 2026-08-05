"""Alert endpoints."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import AlertServiceDep, CurrentUser, ManagerUser
from app.models.enums import AlertSeverity
from app.schemas.alert import AlertCreate, AlertRead, AlertSummary
from app.schemas.common import Message, Page
from app.utils.pagination import Pagination

router = APIRouter()


@router.get("", response_model=Page[AlertRead])
async def list_alerts(
    _user: CurrentUser,
    service: AlertServiceDep,
    params: Pagination,
    severity: AlertSeverity | None = None,
    unread_only: bool = False,
) -> Page[AlertRead]:
    """List alerts, filterable by severity and unread state."""
    items, total = await service.list(
        params, severity=severity, unread_only=unread_only
    )
    return Page.build(
        [AlertRead.model_validate(a) for a in items],
        total,
        params.page,
        params.size,
    )


@router.get("/summary", response_model=AlertSummary)
async def alert_summary(
    _user: CurrentUser, service: AlertServiceDep
) -> AlertSummary:
    """Alert counts by severity plus unread total."""
    return await service.summary()


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate, _manager: ManagerUser, service: AlertServiceDep
) -> AlertRead:
    """Create a manual alert (admin / supply chain manager)."""
    return AlertRead.model_validate(await service.create(data))


@router.patch("/read-all", response_model=Message)
async def mark_all_read(
    _user: CurrentUser, service: AlertServiceDep
) -> Message:
    """Mark every alert as read."""
    count = await service.mark_all_read()
    return Message(message=f"Marked {count} alerts as read.")


@router.patch("/{alert_id}/read", response_model=AlertRead)
async def mark_read(
    alert_id: uuid.UUID, _user: CurrentUser, service: AlertServiceDep
) -> AlertRead:
    """Mark a single alert as read."""
    return AlertRead.model_validate(await service.mark_read(alert_id))


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID, _manager: ManagerUser, service: AlertServiceDep
) -> None:
    """Delete an alert (admin / supply chain manager)."""
    await service.delete(alert_id)
