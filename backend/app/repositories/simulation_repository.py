"""Simulation history repository."""

from app.models.simulation_history import SimulationHistory
from app.repositories.base import BaseRepository


class SimulationRepository(BaseRepository[SimulationHistory]):
    model = SimulationHistory

    async def recent(self, limit: int = 5) -> list[SimulationHistory]:
        items, _ = await self.list(limit=limit)
        return items
