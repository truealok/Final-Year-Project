"""Alert repository."""

from sqlalchemy import func, select, update

from app.models.alert import Alert
from app.models.enums import AlertSeverity
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    async def latest(self, limit: int = 5) -> list[Alert]:
        items, _ = await self.list(limit=limit)
        return items

    async def severity_counts(self) -> dict[str, int]:
        stmt = select(Alert.severity, func.count(Alert.id)).group_by(
            Alert.severity
        )
        result = await self.db.execute(stmt)
        counts = {severity.value: 0 for severity in AlertSeverity}
        for severity, count in result.all():
            counts[severity.value] = int(count)
        return counts

    async def unread_count(self) -> int:
        return await self.count(where=[Alert.is_read.is_(False)])

    async def mark_all_read(self) -> int:
        result = await self.db.execute(
            update(Alert).where(Alert.is_read.is_(False)).values(is_read=True)
        )
        await self.db.flush()
        return int(result.rowcount or 0)
