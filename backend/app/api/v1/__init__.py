"""Version 1 API router assembly."""

from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analytics,
    auth,
    dashboard,
    digital_twin,
    forecast,
    inventory,
    recommendations,
    reports,
    simulation,
    suppliers,
    users,
    warehouses,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
api_router.include_router(
    simulation.router, prefix="/simulation", tags=["Simulation"]
)
api_router.include_router(
    digital_twin.router, prefix="/digital-twin", tags=["Digital Twin"]
)
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])
api_router.include_router(
    warehouses.router, prefix="/warehouses", tags=["Warehouses"]
)
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(
    recommendations.router, prefix="/recommendations", tags=["Recommendations"]
)
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
