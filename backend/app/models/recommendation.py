"""AI-generated resilience recommendations (mock generator today)."""

from typing import Any

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    RecommendationPriority,
    RecommendationStatus,
    enum_column,
)


class Recommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recommendations"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[RecommendationPriority] = mapped_column(
        enum_column(RecommendationPriority),
        default=RecommendationPriority.MEDIUM,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.8, nullable=False
    )  # 0-1
    estimated_savings: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )  # USD
    category: Mapped[str] = mapped_column(
        String(64), default="inventory", nullable=False
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        enum_column(RecommendationStatus),
        default=RecommendationStatus.PENDING,
        nullable=False,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
