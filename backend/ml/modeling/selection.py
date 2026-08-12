"""Best-model selection.

The data decides: models are compared on the SAME held-out validation window
using the configured primary metric (WAPE by default — robust to zero-demand
days). Complexity is never a tie-breaker; the configured secondary metric is.
"""

from __future__ import annotations

import math
from typing import Any


def _metric(metrics: dict[str, Any] | None, name: str) -> float:
    if not metrics:
        return math.inf
    value = metrics.get(name)
    return math.inf if value is None else float(value)


def select_best(
    metrics_by_model: dict[str, dict[str, Any] | None],
    primary_metric: str = "wape",
    tie_breaker: str = "mae",
) -> tuple[str, str]:
    """Return ``(best_model_name, reason)``.

    ``metrics_by_model`` maps model name → validation metrics dict (or None
    when that model failed to train). Raises ``ValueError`` when nothing
    trained successfully.
    """
    candidates = {
        name: m for name, m in metrics_by_model.items() if m is not None
    }
    if not candidates:
        raise ValueError("No successfully trained model to select from")

    ranked = sorted(
        candidates,
        key=lambda name: (
            _metric(candidates[name], primary_metric),
            _metric(candidates[name], tie_breaker),
        ),
    )
    best = ranked[0]
    best_val = _metric(candidates[best], primary_metric)

    if len(ranked) == 1:
        reason = f"only successfully trained model (others failed)"
    else:
        runner = ranked[1]
        runner_val = _metric(candidates[runner], primary_metric)
        if math.isinf(best_val):
            reason = (
                f"selected by {tie_breaker} "
                f"({_metric(candidates[best], tie_breaker):.4g}); "
                f"{primary_metric} undefined for all models"
            )
        elif best_val == runner_val:
            reason = (
                f"tied on {primary_metric} ({best_val:.4g}); selected by "
                f"{tie_breaker} ({_metric(candidates[best], tie_breaker):.4g} "
                f"vs {_metric(candidates[runner], tie_breaker):.4g})"
            )
        else:
            reason = (
                f"lowest validation {primary_metric}: {best_val:.4g} vs "
                f"{runner}={runner_val:.4g}"
            )
    return best, reason
