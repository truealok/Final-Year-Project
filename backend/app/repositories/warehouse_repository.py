"""Warehouse repository."""

from app.models.warehouse import Warehouse
from app.repositories.base import BaseRepository


class WarehouseRepository(BaseRepository[Warehouse]):
    model = Warehouse
