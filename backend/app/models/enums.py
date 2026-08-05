"""Domain enumerations shared by models, schemas and services."""

import enum

from sqlalchemy import Enum as SAEnum


def enum_column(enum_cls: type[enum.Enum]) -> SAEnum:
    """Build a portable (non-native) enum column that stores enum *values*."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=50,
        values_callable=lambda cls: [member.value for member in cls],
    )


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SUPPLY_CHAIN_MANAGER = "supply_chain_manager"
    ANALYST = "analyst"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntityStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISRUPTED = "disrupted"
    MAINTENANCE = "maintenance"


class NodeType(str, enum.Enum):
    SUPPLIER = "supplier"
    FACTORY = "factory"
    WAREHOUSE = "warehouse"
    RETAIL_STORE = "retail_store"


class TransportMode(str, enum.Enum):
    TRUCK = "truck"
    RAIL = "rail"
    SHIP = "ship"
    AIR = "air"


class InventoryStatus(str, enum.Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SimulationType(str, enum.Enum):
    SUPPLIER_FAILURE = "supplier_failure"
    TRANSPORT_DELAY = "transport_delay"
    FLOOD = "flood"
    DEMAND_SPIKE = "demand_spike"
    WAREHOUSE_FAILURE = "warehouse_failure"
    MACHINE_BREAKDOWN = "machine_breakdown"


class SeverityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ForecastModel(str, enum.Enum):
    PROPHET = "prophet"
    XGBOOST = "xgboost"
    LSTM = "lstm"


class RecommendationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"


class ReportType(str, enum.Enum):
    FORECAST = "forecast"
    SIMULATION = "simulation"
    INVENTORY = "inventory"
    RISK = "risk"


class ReportFormat(str, enum.Enum):
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
