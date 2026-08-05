"""FastAPI dependency injection wiring.

Routes depend on services; services receive repositories; repositories
receive the request-scoped database session. Nothing below the controller
layer imports FastAPI request machinery.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories import (
    AlertRepository,
    CategoryRepository,
    FactoryRepository,
    ForecastRepository,
    InventoryRepository,
    ProductRepository,
    RecommendationRepository,
    ReportRepository,
    RetailStoreRepository,
    SalesRepository,
    SimulationRepository,
    SupplierRepository,
    TransportRouteRepository,
    UserRepository,
    WarehouseRepository,
)
from app.services.alert_service import AlertService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.dashboard_service import DashboardService
from app.services.digital_twin_service import DigitalTwinService
from app.services.forecast_service import ForecastService
from app.services.inventory_service import InventoryService
from app.services.recommendation_service import RecommendationService
from app.services.report_service import ReportService
from app.services.simulation_service import SimulationService
from app.services.supplier_service import SupplierService
from app.services.user_service import UserService
from app.services.warehouse_service import WarehouseService
from app.utils.exceptions import ForbiddenError, UnauthorizedError

DbSession = Annotated[AsyncSession, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token"
)


# --------------------------------------------------------------------------- #
# Authentication / authorization
# --------------------------------------------------------------------------- #
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    payload = decode_token(token, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Could not validate credentials.") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User no longer exists or is inactive.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Build a dependency that allows only the given roles."""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError(
                "This action requires one of the roles: "
                + ", ".join(role.value for role in roles)
            )
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
ManagerUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER)),
]


# --------------------------------------------------------------------------- #
# Service providers
# --------------------------------------------------------------------------- #
def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db))


def get_user_service(db: DbSession) -> UserService:
    return UserService(UserRepository(db))


def get_supplier_service(db: DbSession) -> SupplierService:
    return SupplierService(SupplierRepository(db))


def get_warehouse_service(db: DbSession) -> WarehouseService:
    return WarehouseService(WarehouseRepository(db), InventoryRepository(db))


def get_inventory_service(db: DbSession) -> InventoryService:
    return InventoryService(
        InventoryRepository(db),
        ProductRepository(db),
        CategoryRepository(db),
        WarehouseRepository(db),
    )


def get_forecast_service(db: DbSession) -> ForecastService:
    return ForecastService(
        ForecastRepository(db), ProductRepository(db), WarehouseRepository(db)
    )


def get_simulation_service(db: DbSession) -> SimulationService:
    return SimulationService(
        SimulationRepository(db), SupplierRepository(db), WarehouseRepository(db)
    )


def get_digital_twin_service(db: DbSession) -> DigitalTwinService:
    return DigitalTwinService(
        SupplierRepository(db),
        FactoryRepository(db),
        WarehouseRepository(db),
        RetailStoreRepository(db),
        TransportRouteRepository(db),
        InventoryRepository(db),
    )


def get_dashboard_service(db: DbSession) -> DashboardService:
    return DashboardService(
        AlertRepository(db), SimulationRepository(db), InventoryRepository(db)
    )


def get_analytics_service(db: DbSession) -> AnalyticsService:
    return AnalyticsService(
        SalesRepository(db),
        SupplierRepository(db),
        WarehouseRepository(db),
        InventoryRepository(db),
        SimulationRepository(db),
    )


def get_recommendation_service(db: DbSession) -> RecommendationService:
    return RecommendationService(RecommendationRepository(db))


def get_report_service(db: DbSession) -> ReportService:
    return ReportService(
        ReportRepository(db),
        ForecastRepository(db),
        SimulationRepository(db),
        InventoryRepository(db),
        SupplierRepository(db),
        AlertRepository(db),
    )


def get_alert_service(db: DbSession) -> AlertService:
    return AlertService(AlertRepository(db))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
SupplierServiceDep = Annotated[SupplierService, Depends(get_supplier_service)]
WarehouseServiceDep = Annotated[WarehouseService, Depends(get_warehouse_service)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
SimulationServiceDep = Annotated[
    SimulationService, Depends(get_simulation_service)
]
DigitalTwinServiceDep = Annotated[
    DigitalTwinService, Depends(get_digital_twin_service)
]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
RecommendationServiceDep = Annotated[
    RecommendationService, Depends(get_recommendation_service)
]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
AlertServiceDep = Annotated[AlertService, Depends(get_alert_service)]
