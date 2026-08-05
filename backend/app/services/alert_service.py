"""Alert business logic."""

import uuid

from app.models.alert import Alert
from app.models.enums import AlertSeverity
from app.repositories.alert_repository import AlertRepository
from app.schemas.alert import AlertCreate, AlertSummary
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PaginationParams


class AlertService:
    def __init__(self, alerts: AlertRepository) -> None:
        self.alerts = alerts

    async def list(
        self,
        params: PaginationParams,
        *,
        severity: AlertSeverity | None = None,
        unread_only: bool = False,
    ) -> tuple[list[Alert], int]:
        where = []
        if severity:
            where.append(Alert.severity == severity)
        if unread_only:
            where.append(Alert.is_read.is_(False))
        return await self.alerts.list(
            offset=params.offset, limit=params.size, where=where
        )

    async def get(self, alert_id: uuid.UUID) -> Alert:
        alert = await self.alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("Alert not found.")
        return alert

    async def create(self, data: AlertCreate) -> Alert:
        return await self.alerts.create(**data.model_dump())

    async def mark_read(self, alert_id: uuid.UUID) -> Alert:
        alert = await self.get(alert_id)
        return await self.alerts.update(alert, is_read=True)

    async def mark_all_read(self) -> int:
        return await self.alerts.mark_all_read()

    async def delete(self, alert_id: uuid.UUID) -> None:
        alert = await self.get(alert_id)
        await self.alerts.delete(alert)

    async def summary(self) -> AlertSummary:
        counts = await self.alerts.severity_counts()
        return AlertSummary(
            total=sum(counts.values()),
            unread=await self.alerts.unread_count(),
            critical=counts.get("critical", 0),
            warning=counts.get("warning", 0),
            info=counts.get("info", 0),
        )
