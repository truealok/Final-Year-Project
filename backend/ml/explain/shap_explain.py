"""Model explainability.

- **XGBoost** → SHAP ``TreeExplainer``: global importance (mean |SHAP|),
  signed mean contribution (top positive / negative drivers) and a beeswarm
  summary figure. All values come from the trained model on real feature
  rows — nothing is invented.
- **Prophet** → SHAP does not apply to Prophet; its native forecast
  decomposition (trend / weekly / yearly components) is exported instead.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")  # headless — figures go to files only
import matplotlib.pyplot as plt  # noqa: E402  (after backend selection)

from ml.modeling.prophet_model import ProphetForecaster  # noqa: E402
from ml.modeling.xgboost_model import XGBForecaster  # noqa: E402


def explain_xgboost(
    forecaster: XGBForecaster,
    features: pd.DataFrame,
    out_dir: str | Path | None = None,
    max_display: int = 15,
) -> dict[str, Any]:
    """SHAP-explain a trained XGBForecaster on *features* rows.

    *features* must contain the model's feature columns (e.g. the supervised
    frame from training). Returns an importance report dict; when *out_dir*
    is given also writes ``feature_importance.json`` and ``shap_summary.png``.
    """
    import shap

    if forecaster.model is None:
        raise RuntimeError("explain_xgboost needs a fitted model")
    cols = forecaster.feature_cols
    x = features[cols].to_numpy(dtype=float)

    explainer = shap.TreeExplainer(forecaster.model)
    shap_values = explainer.shap_values(x)

    mean_abs = np.abs(shap_values).mean(axis=0)
    mean_signed = shap_values.mean(axis=0)
    order = np.argsort(mean_abs)[::-1]

    importance = {cols[i]: round(float(mean_abs[i]), 4) for i in order}
    signed = {cols[i]: round(float(mean_signed[i]), 4) for i in order}
    top_positive = {
        k: v for k, v in sorted(signed.items(), key=lambda kv: -kv[1]) if v > 0
    }
    top_negative = {
        k: v for k, v in sorted(signed.items(), key=lambda kv: kv[1]) if v < 0
    }

    report: dict[str, Any] = {
        "method": "shap.TreeExplainer",
        "n_rows_explained": int(x.shape[0]),
        "feature_importance": importance,  # mean |SHAP|, descending
        "mean_signed_contribution": signed,
        "top_positive_features": dict(list(top_positive.items())[:5]),
        "top_negative_features": dict(list(top_negative.items())[:5]),
        "expected_value": round(float(np.ravel(explainer.expected_value)[0]), 4),
    }

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "feature_importance.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        plt.figure()
        shap.summary_plot(
            shap_values,
            features[cols],
            max_display=max_display,
            show=False,
        )
        plt.tight_layout()
        plt.savefig(out / "shap_summary.png", dpi=120)
        plt.close("all")
    return report


def prophet_components(
    forecaster: ProphetForecaster,
    dates: pd.DatetimeIndex,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Export Prophet's native decomposition (NOT SHAP — see module docs)."""
    comp = forecaster.components(dates)
    report: dict[str, Any] = {
        "method": "prophet.native_components",
        "note": "SHAP does not apply to Prophet; this is the model's own "
        "trend/seasonality decomposition.",
        "trend_start": round(float(comp["trend"].iloc[0]), 2),
        "trend_end": round(float(comp["trend"].iloc[-1]), 2),
        "trend_change": round(
            float(comp["trend"].iloc[-1] - comp["trend"].iloc[0]), 2
        ),
    }
    if "weekly" in comp.columns:
        weekly = comp.groupby(comp["date"].dt.weekday)["weekly"].mean()
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        report["weekly_effect"] = {
            names[int(d)]: round(float(v), 2) for d, v in weekly.items()
        }
    if "yearly" in comp.columns:
        report["yearly_effect_range"] = [
            round(float(comp["yearly"].min()), 2),
            round(float(comp["yearly"].max()), 2),
        ]

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "prophet_components.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        fig, axes = plt.subplots(
            len([c for c in comp.columns if c != "date"]),
            1,
            figsize=(9, 6),
            sharex=False,
        )
        axes = np.atleast_1d(axes)
        for ax, col in zip(axes, [c for c in comp.columns if c != "date"]):
            ax.plot(comp["date"], comp[col])
            ax.set_title(col)
        fig.tight_layout()
        fig.savefig(out / "prophet_components.png", dpi=120)
        plt.close(fig)
    return report
