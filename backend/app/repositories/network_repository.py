"""Repositories for network entities: factories, retail stores, routes."""

from app.models.factory import Factory
from app.models.retail_store import RetailStore
from app.models.transport_route import TransportRoute
from app.repositories.base import BaseRepository


class FactoryRepository(BaseRepository[Factory]):
    model = Factory


class RetailStoreRepository(BaseRepository[RetailStore]):
    model = RetailStore


class TransportRouteRepository(BaseRepository[TransportRoute]):
    model = TransportRoute
