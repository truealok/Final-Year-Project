"""Recommendation endpoints."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, RecommendationServiceDep
from app.models.enums import RecommendationPriority, RecommendationStatus
from app.schemas.common import Page
from app.schemas.recommendation import (
    RecommendationRead,
    RecommendationStatusUpdate,
)
from app.utils.pagination import Pagination

router = APIRouter()


@router.get("", response_model=Page[RecommendationRead])
async def list_recommendations(
    _user: CurrentUser,
    service: RecommendationServiceDep,
    params: Pagination,
    priority: RecommendationPriority | None = None,
    status_filter: RecommendationStatus | None = None,
    category: str | None = None,
) -> Page[RecommendationRead]:
    """List AI recommendations with priority/status/category filters."""
    items, total = await service.list(
        params, priority=priority, status=status_filter, category=category
    )
    return Page.build(
        [RecommendationRead.model_validate(r) for r in items],
        total,
        params.page,
        params.size,
    )


@router.post(
    "/generate",
    response_model=list[RecommendationRead],
    status_code=status.HTTP_201_CREATED,
)
async def generate_recommendations(
    _user: CurrentUser, service: RecommendationServiceDep
) -> list[RecommendationRead]:
    """Generate a fresh batch of recommendations (mock engine)."""
    created = await service.generate()
    return [RecommendationRead.model_validate(r) for r in created]


@router.patch("/{recommendation_id}", response_model=RecommendationRead)
async def update_recommendation_status(
    recommendation_id: uuid.UUID,
    data: RecommendationStatusUpdate,
    _user: CurrentUser,
    service: RecommendationServiceDep,
) -> RecommendationRead:
    """Apply or dismiss a recommendation."""
    updated = await service.update_status(recommendation_id, data.status)
    return RecommendationRead.model_validate(updated)
