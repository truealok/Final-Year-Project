"""Integration layer between the FastAPI backend and the ``ml`` package."""

from app.services.ml.adapter import MLForecastEngine, ml_engine

__all__ = ["MLForecastEngine", "ml_engine"]
