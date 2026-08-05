"""Repository layer - all database access lives here (Repository pattern)."""

from app.repositories.base import BaseRepository
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import (
    CategoryRepository,
    ProductRepository,
)
from app.repositories.supplier_repository import SupplierRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.network_repository import (
    FactoryRepository,
    RetailStoreRepository,
    TransportRouteRepository,
)
from app.repositories.sales_repository import SalesRepository
from app.repositories.forecast_repository import ForecastRepository
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.report_repository import ReportRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "CategoryRepository",
    "ProductRepository",
    "SupplierRepository",
    "WarehouseRepository",
    "InventoryRepository",
    "FactoryRepository",
    "RetailStoreRepository",
    "TransportRouteRepository",
    "SalesRepository",
    "ForecastRepository",
    "SimulationRepository",
    "RecommendationRepository",
    "AlertRepository",
    "ReportRepository",
]
