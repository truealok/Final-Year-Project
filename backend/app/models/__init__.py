"""SQLAlchemy ORM models.

Importing this package registers every model on ``Base.metadata`` — required
by Alembic autogenerate and ``init_db``.
"""

from app.models.base import Base
from app.models.enums import (
    AlertSeverity,
    EntityStatus,
    ForecastModel,
    InventoryStatus,
    NodeType,
    RecommendationPriority,
    RecommendationStatus,
    ReportFormat,
    ReportType,
    RiskLevel,
    SeverityLevel,
    SimulationType,
    TransportMode,
    UserRole,
)
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.factory import Factory
from app.models.warehouse import Warehouse
from app.models.retail_store import RetailStore
from app.models.transport_route import TransportRoute
from app.models.inventory import Inventory
from app.models.sales_history import SalesHistory
from app.models.forecast_history import ForecastHistory
from app.models.simulation_history import SimulationHistory
from app.models.recommendation import Recommendation
from app.models.alert import Alert
from app.models.report import Report
from app.models.setting import Setting

__all__ = [
    "Base",
    "User",
    "Category",
    "Product",
    "Supplier",
    "Factory",
    "Warehouse",
    "RetailStore",
    "TransportRoute",
    "Inventory",
    "SalesHistory",
    "ForecastHistory",
    "SimulationHistory",
    "Recommendation",
    "Alert",
    "Report",
    "Setting",
    "UserRole",
    "RiskLevel",
    "EntityStatus",
    "NodeType",
    "TransportMode",
    "InventoryStatus",
    "AlertSeverity",
    "SimulationType",
    "SeverityLevel",
    "ForecastModel",
    "RecommendationPriority",
    "RecommendationStatus",
    "ReportType",
    "ReportFormat",
]
