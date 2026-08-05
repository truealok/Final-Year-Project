"""Recommendation repository."""

from app.models.recommendation import Recommendation
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation
