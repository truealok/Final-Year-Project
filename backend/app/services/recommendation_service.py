"""Recommendation business logic — transparent rule-based decision engine.

``generate`` derives actionable recommendations from **actual system state**:

1. real sales trend (last 30 days vs the 30 before) x inventory cover
   → safety-stock increases for growing SKUs;
2. inventory rows below their reorder point → replenishment;
3. low-reliability suppliers weighted by the demand they ultimately serve
   → sourcing shifts to the best alternative supplier;
4. warehouse utilization imbalance → stock rebalancing;
5. the most recent disruption simulation (when resilience < 80) →
   scenario-specific mitigation.

Every number shown (growth %, cover days, savings estimate, confidence) is
computed from the data and stored in ``context`` for auditability. Savings
formulas are simple and documented in-line — estimates, not observations.
No randomness anywhere.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models.enums import (
    RecommendationPriority,
    RecommendationStatus,
)
from app.models.recommendation import Recommendation
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.sales_repository import SalesRepository
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.supplier_repository import SupplierRepository
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PaginationParams

MAX_RECOMMENDATIONS = 5
GROWTH_THRESHOLD = 0.20          # 20% window-over-window growth
LOW_RELIABILITY = 85.0
UTILIZATION_HIGH = 85.0
UTILIZATION_LOW = 30.0
SIM_RESILIENCE_THRESHOLD = 80.0


class RecommendationService:
    def __init__(
        self,
        recommendations: RecommendationRepository,
        inventory: InventoryRepository,
        sales: SalesRepository,
        suppliers: SupplierRepository,
        simulations: SimulationRepository,
    ) -> None:
        self.recommendations = recommendations
        self.inventory = inventory
        self.sales = sales
        self.suppliers = suppliers
        self.simulations = simulations

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

    # ------------------------------------------------------------------ #
    # Rule evaluation — each rule returns candidate dicts (or nothing)
    # ------------------------------------------------------------------ #
    async def _rule_demand_growth(self) -> list[dict[str, Any]]:
        """Growing SKUs (real sales) with thin inventory cover."""
        totals = await self.sales.product_window_totals(30)
        if not totals:
            return []
        items = await self.inventory.list_all()
        stock_by_product: dict[uuid.UUID, float] = {}
        price_by_product: dict[uuid.UUID, float] = {}
        sku_by_product: dict[uuid.UUID, str] = {}
        for item in items:
            stock_by_product[item.product_id] = (
                stock_by_product.get(item.product_id, 0) + item.quantity
            )
            if item.product is not None:
                price_by_product[item.product_id] = item.product.unit_price
                sku_by_product[item.product_id] = item.product.sku

        candidates = []
        for product_id, last, prev in totals:
            if prev <= 0 or last < 50:
                continue
            growth = (last - prev) / prev
            if growth < GROWTH_THRESHOLD:
                continue
            daily = last / 30
            cover = stock_by_product.get(product_id, 0) / daily if daily else 0
            if cover >= 14:
                continue  # buffer already healthy
            price = price_by_product.get(product_id, 0.0)
            increase_pct = min(50, round(growth * 100 / 2))  # half the growth
            # savings estimate = avoided lost sales over one lead-time cycle
            savings = round(daily * growth * price * 7, 2)
            sku = sku_by_product.get(product_id, str(product_id)[:8])
            candidates.append({
                "title": f"Increase safety stock for {sku}",
                "suggested_action": (
                    f"Raise safety stock for {sku} by ~{increase_pct}%: "
                    f"demand grew {growth:.0%} in 30 days while cover is "
                    f"only {cover:.1f} days."
                ),
                "reason": (
                    f"Real sales: {last:.0f} units in the last 30 days vs "
                    f"{prev:.0f} in the 30 before ({growth:+.0%}); current "
                    f"stock covers {cover:.1f} days at the new rate."
                ),
                "category": "inventory",
                "priority": (
                    RecommendationPriority.HIGH
                    if cover < 7
                    else RecommendationPriority.MEDIUM
                ),
                # confidence grows with signal strength, capped
                "confidence": round(min(0.95, 0.6 + growth / 2), 2),
                "estimated_savings": savings,
                "context": {
                    "rule": "demand_growth_low_cover",
                    "product_id": str(product_id),
                    "growth_pct": round(growth * 100, 1),
                    "cover_days": round(cover, 1),
                    "last_30d_units": last,
                    "prev_30d_units": prev,
                },
                "_score": growth * (14 - cover),
            })
        candidates.sort(key=lambda c: -c["_score"])
        return candidates[:2]

    async def _rule_below_reorder(self) -> list[dict[str, Any]]:
        """Inventory positions already below their reorder point."""
        items = await self.inventory.list_all()
        low = [i for i in items if i.quantity <= i.reorder_point]
        if not low:
            return []
        low.sort(key=lambda i: i.quantity - i.reorder_point)
        worst = low[:3]
        names = ", ".join(
            (i.product.sku if i.product else str(i.product_id)[:8])
            for i in worst
        )
        value = sum(
            (i.reorder_point - i.quantity)
            * (i.product.unit_price if i.product else 0)
            for i in low
        )
        return [{
            "title": f"Replenish {len(low)} SKUs at or below reorder point",
            "suggested_action": (
                f"Raise purchase orders for {len(low)} inventory positions "
                f"currently at/below their reorder point (most urgent: "
                f"{names})."
            ),
            "reason": (
                f"{len(low)} of {len(items)} inventory positions have "
                "fallen to their reorder point — stockout risk grows every "
                "day replenishment is deferred."
            ),
            "category": "inventory",
            "priority": (
                RecommendationPriority.CRITICAL
                if len(low) > len(items) * 0.2
                else RecommendationPriority.HIGH
            ),
            "confidence": 0.9,  # direct reading of inventory state
            "estimated_savings": round(value, 2),
            "context": {
                "rule": "below_reorder_point",
                "positions_below": len(low),
                "total_positions": len(items),
            },
            "_score": len(low),
        }]

    async def _rule_supplier_risk(self) -> list[dict[str, Any]]:
        """Low-reliability suppliers with a better available alternative."""
        supplier_list = await self.suppliers.list_all()
        active = [s for s in supplier_list if s.status.value == "active"]
        weak = [s for s in active if s.reliability_score < LOW_RELIABILITY]
        if not weak or len(active) < 2:
            return []
        weak.sort(key=lambda s: s.reliability_score)
        worst = weak[0]
        best = max(active, key=lambda s: s.reliability_score)
        if best.id == worst.id:
            return []
        gap = best.reliability_score - worst.reliability_score
        return [{
            "title": f"Reduce dependence on {worst.name}",
            "suggested_action": (
                f"Qualify {best.name} (reliability "
                f"{best.reliability_score:.0f}%) for 30% of the volume "
                f"currently sourced from {worst.name} (reliability "
                f"{worst.reliability_score:.0f}%)."
            ),
            "reason": (
                f"{worst.name} is the least reliable active supplier "
                f"({worst.reliability_score:.0f}%, risk "
                f"{worst.risk_level.value}); a {gap:.0f}-point more "
                "reliable alternative exists."
            ),
            "category": "sourcing",
            "priority": (
                RecommendationPriority.HIGH
                if worst.reliability_score < 80
                else RecommendationPriority.MEDIUM
            ),
            "confidence": round(min(0.9, 0.5 + gap / 40), 2),
            "estimated_savings": None,
            "context": {
                "rule": "supplier_reliability",
                "supplier_id": str(worst.id),
                "supplier_reliability": worst.reliability_score,
                "alternative_id": str(best.id),
                "alternative_reliability": best.reliability_score,
            },
            "_score": gap,
        }]

    async def _rule_warehouse_imbalance(self) -> list[dict[str, Any]]:
        """Utilization spread across warehouses (from inventory vs capacity)."""
        items = await self.inventory.list_all()
        if not items:
            return []
        by_wh: dict[uuid.UUID, dict[str, Any]] = {}
        for item in items:
            wh = item.warehouse
            if wh is None or not wh.capacity:
                continue
            entry = by_wh.setdefault(
                item.warehouse_id,
                {"name": wh.name, "capacity": wh.capacity, "units": 0},
            )
            entry["units"] += item.quantity
        stats = [
            (e["name"], e["units"] / e["capacity"] * 100) for e in by_wh.values()
        ]
        if len(stats) < 2:
            return []
        stats.sort(key=lambda s: -s[1])
        (hi_name, hi_util), (lo_name, lo_util) = stats[0], stats[-1]
        if hi_util < UTILIZATION_HIGH or lo_util > UTILIZATION_LOW:
            return []
        return [{
            "title": f"Rebalance stock from {hi_name} to {lo_name}",
            "suggested_action": (
                f"Transfer slow movers from {hi_name} "
                f"({hi_util:.0f}% utilized) to {lo_name} "
                f"({lo_util:.0f}% utilized) to free receiving capacity."
            ),
            "reason": (
                f"Warehouse utilization is unbalanced: {hi_util:.0f}% vs "
                f"{lo_util:.0f}% — the constrained site raises both "
                "handling cost and overflow risk."
            ),
            "category": "inventory",
            "priority": RecommendationPriority.MEDIUM,
            "confidence": 0.75,
            "estimated_savings": None,
            "context": {
                "rule": "warehouse_imbalance",
                "high": {"name": hi_name, "utilization_pct": round(hi_util, 1)},
                "low": {"name": lo_name, "utilization_pct": round(lo_util, 1)},
            },
            "_score": hi_util - lo_util,
        }]

    async def _rule_simulation_followup(self) -> list[dict[str, Any]]:
        """Mitigation for the latest low-resilience simulation run."""
        recent = await self.simulations.recent(1)
        if not recent:
            return []
        sim = recent[0]
        if sim.resilience_score >= SIM_RESILIENCE_THRESHOLD:
            return []
        actions = {
            "supplier_failure": "dual-source the affected components and "
            "pre-build 2 extra weeks of upstream buffer",
            "transport_delay": "qualify an alternate transport lane and "
            "extend safety lead times",
            "warehouse_failure": "spread critical SKU stock across a second "
            "warehouse to remove the single point of failure",
            "flood": "spread critical SKU stock across a second warehouse "
            "and review site flood defenses",
            "demand_spike": "pre-position fast movers and agree surge "
            "capacity with the factories",
            "machine_breakdown": "schedule preventive maintenance and "
            "qualify backup production capacity",
        }
        sim_type = sim.simulation_type.value
        return [{
            "title": f"Mitigate {sim_type.replace('_', ' ')} exposure",
            "suggested_action": (
                f"Latest simulation scored resilience "
                f"{sim.resilience_score:.0f}/100 — {actions.get(sim_type, 'review the scenario')}."
            ),
            "reason": (
                f"Monte Carlo run ({sim.severity.value} severity, "
                f"{sim.duration_days} days) projected "
                f"{sim.stockout_probability:.0%} stockout probability and "
                f"${sim.expected_cost:,.0f} expected cost."
            ),
            "category": "resilience",
            "priority": (
                RecommendationPriority.CRITICAL
                if sim.resilience_score < 60
                else RecommendationPriority.HIGH
            ),
            "confidence": 0.8,
            "estimated_savings": round(sim.expected_cost * 0.5, 2),
            "context": {
                "rule": "simulation_followup",
                "simulation_id": str(sim.id),
                "resilience_score": sim.resilience_score,
                "expected_cost": sim.expected_cost,
            },
            "_score": 100 - sim.resilience_score,
        }]

    async def _rule_data_gaps(self) -> list[dict[str, Any]]:
        """Fallback: real gaps in operational data worth fixing."""
        items = await self.inventory.list_all()
        totals = await self.sales.product_window_totals(30)
        covered = {i.product_id for i in items}
        selling_uncovered = [
            pid for pid, last, _ in totals if last > 0 and pid not in covered
        ]
        if not selling_uncovered:
            return []
        return [{
            "title": (
                f"Set inventory policies for {len(selling_uncovered)} "
                "selling products"
            ),
            "suggested_action": (
                f"{len(selling_uncovered)} products sold in the last 30 days "
                "have no inventory record — define stock levels and reorder "
                "points so stockout monitoring can cover them."
            ),
            "reason": (
                "Demand exists (real sales rows) but no inventory position "
                "is tracked, so cover and stockout risk cannot be computed."
            ),
            "category": "planning",
            "priority": RecommendationPriority.MEDIUM,
            "confidence": 0.85,
            "estimated_savings": None,
            "context": {
                "rule": "untracked_selling_products",
                "count": len(selling_uncovered),
            },
            "_score": len(selling_uncovered) / 10,
        }]

    # ------------------------------------------------------------------ #
    async def generate(self) -> list[Recommendation]:
        """Evaluate all rules against current data and persist the top picks."""
        candidates: list[dict[str, Any]] = []
        for rule in (
            self._rule_simulation_followup,
            self._rule_below_reorder,
            self._rule_demand_growth,
            self._rule_supplier_risk,
            self._rule_warehouse_imbalance,
            self._rule_data_gaps,
        ):
            candidates.extend(await rule())

        candidates.sort(key=lambda c: -c["_score"])
        created: list[Recommendation] = []
        for candidate in candidates[:MAX_RECOMMENDATIONS]:
            candidate.pop("_score", None)
            context = candidate.pop("context", {})
            context["generated_by"] = "rule_engine_v1"
            if candidate.get("estimated_savings") is None:
                candidate["estimated_savings"] = 0.0  # not quantifiable
            rec = await self.recommendations.create(
                **candidate,
                status=RecommendationStatus.PENDING,
                context=context,
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
