"""Recommendation schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import RecommendationPriority, RecommendationStatus


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    suggested_action: str
    reason: str
    priority: RecommendationPriority
    confidence: float
    estimated_savings: float
    category: str
    status: RecommendationStatus
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RecommendationStatusUpdate(BaseModel):
    status: RecommendationStatus
