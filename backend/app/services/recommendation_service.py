"""Recommendation business logic.

The generator is a rules/mock engine today; a real optimization model can
replace ``generate`` without touching the API contract.
"""

import random
import uuid

from app.models.enums import RecommendationPriority, RecommendationStatus
from app.models.recommendation import Recommendation
from app.repositories.recommendation_repository import RecommendationRepository
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PaginationParams

_TEMPLATES: list[dict] = [
    {
        "title": "Increase safety stock for high-velocity SKUs",
        "suggested_action": (
            "Raise safety stock by 15-20% for the top 10 SKUs by demand "
            "volatility at the primary distribution warehouses."
        ),
        "reason": (
            "Recent demand variability exceeded the current safety stock "
            "coverage, raising projected stockout probability above 12%."
        ),
        "category": "inventory",
    },
    {
        "title": "Switch to alternate supplier for critical components",
        "suggested_action": (
            "Qualify and shift 30% of order volume to a secondary supplier "
            "with higher reliability in a different geographic region."
        ),
        "reason": (
            "Primary supplier reliability dropped below 80% and carries "
            "elevated regional risk exposure."
        ),
        "category": "sourcing",
    },
    {
        "title": "Use alternate transport route to avoid congestion",
        "suggested_action": (
            "Reroute shipments via the rail corridor for the next 2 weeks "
            "to bypass congested port operations."
        ),
        "reason": (
            "Transit times on the current route increased 35% over the "
            "trailing 14 days."
        ),
        "category": "logistics",
    },
    {
        "title": "Rebalance inventory across regional warehouses",
        "suggested_action": (
            "Transfer excess stock from low-demand to high-demand regions "
            "to cut expedited-freight spend."
        ),
        "reason": (
            "Warehouse utilization is unbalanced (91% vs 42%), increasing "
            "both stockout and holding-cost risk."
        ),
        "category": "inventory",
    },
    {
        "title": "Pre-position stock ahead of seasonal demand spike",
        "suggested_action": (
            "Build 3 additional weeks of coverage for seasonal SKUs before "
            "the forecast peak window."
        ),
        "reason": (
            "Forecast models project a 28% seasonal demand increase with "
            "high confidence."
        ),
        "category": "planning",
    },
]


class RecommendationService:
    def __init__(self, recommendations: RecommendationRepository) -> None:
        self.recommendations = recommendations

    async def list(
        self,
        params: PaginationParams,
        *,
        priority: RecommendationPriority | None = None,
        status: RecommendationStatus | None = None,
        category: str | None = None,
    ) -> tuple[list[Recommendation], int]:
        where = []
        if priority:
            where.append(Recommendation.priority == priority)
        if status:
            where.append(Recommendation.status == status)
        if category:
            where.append(Recommendation.category == category)
        return await self.recommendations.list(
            offset=params.offset, limit=params.size, where=where
        )

    async def generate(self) -> list[Recommendation]:
        """Create a fresh batch of mock recommendations."""
        rng = random.Random()
        created: list[Recommendation] = []
        priorities = list(RecommendationPriority)
        for template in rng.sample(_TEMPLATES, k=3):
            rec = await self.recommendations.create(
                **template,
                priority=rng.choice(priorities),
                confidence=round(rng.uniform(0.7, 0.97), 2),
                estimated_savings=round(rng.uniform(15_000, 250_000), 2),
                status=RecommendationStatus.PENDING,
                context={"generated_by": "mock_engine_v1"},
            )
            created.append(rec)
        return created

    async def update_status(
        self, recommendation_id: uuid.UUID, status: RecommendationStatus
    ) -> Recommendation:
        rec = await self.recommendations.get(recommendation_id)
        if rec is None:
            raise NotFoundError("Recommendation not found.")
        return await self.recommendations.update(rec, status=status)
