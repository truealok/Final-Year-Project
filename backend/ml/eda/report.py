"""Exploratory data analysis.

``run_eda`` computes statistics and saves six figures under
``ml/artifacts/eda/`` plus ``eda_report.json``. Conclusions are **derived
from the data** (trend fitted, seasonality measured) — never hardcoded.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_CAL = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _fig(path: Path, title: str) -> None:
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close("all")


def run_eda(
    df: pd.DataFrame,
    out_dir: str | Path,
    product_index: pd.DataFrame | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """Analyze a preprocessed canonical frame; returns the report dict.

    *product_index* (optional, columns product_id/sku/name) makes labels
    human-readable.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])

    labels = {}
    if product_index is not None:
        labels = dict(
            zip(product_index["product_id"], product_index["sku"], strict=False)
        )

    def label(pid: str) -> str:
        return labels.get(pid, str(pid)[:8])

    # ---------------- aggregate series ------------------------------- #
    daily = d.groupby("date", as_index=False)["demand"].sum()
    monthly = (
        d.assign(month=d["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["demand"]
        .sum()
    )
    weekday = d.groupby(d["date"].dt.weekday)["demand"].mean()
    by_product = (
        d.groupby("product_id")["demand"].sum().sort_values(ascending=False)
    )

    # ---------------- data-driven conclusions ------------------------- #
    x = np.arange(len(daily))
    slope, intercept = np.polyfit(x, daily["demand"].to_numpy(dtype=float), 1)
    mean_daily = float(daily["demand"].mean())
    trend_pct_per_30d = (
        (slope * 30) / mean_daily * 100 if mean_daily else 0.0
    )
    trend_direction = (
        "increasing" if trend_pct_per_30d > 1
        else "decreasing" if trend_pct_per_30d < -1
        else "flat"
    )
    weekday_ratio = (
        float(weekday.max() / weekday.min()) if weekday.min() > 0 else None
    )
    peak_month = monthly.loc[monthly["demand"].idxmax(), "month"]
    low_month = monthly.loc[monthly["demand"].idxmin(), "month"]
    zero_share = float((d["demand"] == 0).mean())
    outlier_share = (
        float(d["is_outlier"].mean()) if "is_outlier" in d.columns else None
    )

    report: dict[str, Any] = {
        "rows": int(len(d)),
        "products": int(d["product_id"].nunique()),
        "warehouses": int(d["warehouse_id"].nunique(dropna=True)),
        "date_range": [
            str(d["date"].min().date()),
            str(d["date"].max().date()),
        ],
        "total_demand": float(d["demand"].sum()),
        "mean_daily_total_demand": round(mean_daily, 2),
        "trend": {
            "direction": trend_direction,
            "slope_units_per_day": round(float(slope), 4),
            "pct_change_per_30_days": round(trend_pct_per_30d, 2),
        },
        "weekly_seasonality": {
            "mean_demand_by_weekday": {
                _CAL[int(i)]: round(float(v), 2) for i, v in weekday.items()
            },
            "peak_weekday": _CAL[int(weekday.idxmax())],
            "trough_weekday": _CAL[int(weekday.idxmin())],
            "peak_to_trough_ratio": (
                round(weekday_ratio, 3) if weekday_ratio else None
            ),
        },
        "monthly": {
            "peak_month": str(peak_month),
            "lowest_month": str(low_month),
        },
        "distribution": {
            "min": float(d["demand"].min()),
            "p25": float(d["demand"].quantile(0.25)),
            "median": float(d["demand"].median()),
            "p75": float(d["demand"].quantile(0.75)),
            "max": float(d["demand"].max()),
            "zero_demand_share": round(zero_share, 4),
            "outlier_share": (
                round(outlier_share, 4) if outlier_share is not None else None
            ),
        },
        "top_products_by_total_demand": {
            label(pid): float(v) for pid, v in by_product.head(top_n).items()
        },
    }

    conclusions = [
        f"Overall demand trend is {trend_direction} "
        f"({trend_pct_per_30d:+.1f}% per 30 days).",
        f"Weekly seasonality: peak on {report['weekly_seasonality']['peak_weekday']}, "
        f"trough on {report['weekly_seasonality']['trough_weekday']}"
        + (
            f" (ratio {weekday_ratio:.2f})." if weekday_ratio else "."
        ),
        f"Peak month {peak_month}, lowest month {low_month}.",
        f"{zero_share:.1%} of series-days have zero demand — plain MAPE is "
        "unreliable; sMAPE/WAPE reported alongside.",
    ]
    span_days = (d["date"].max() - d["date"].min()).days + 1
    if span_days < 730:
        conclusions.append(
            f"History spans {span_days} days (<2 yearly cycles) — yearly "
            "seasonality cannot be separated from trend and stays disabled."
        )
    report["conclusions"] = conclusions

    # ---------------- figures ----------------------------------------- #
    # 1. historical total demand trend
    plt.figure(figsize=(10, 4))
    plt.plot(daily["date"], daily["demand"], linewidth=0.8)
    trend_line = intercept + slope * x
    plt.plot(daily["date"], trend_line, "--")
    _fig(out / "01_daily_demand_trend.png", "Total daily demand (with linear trend)")

    # 2. monthly demand
    plt.figure(figsize=(10, 4))
    plt.bar(monthly["month"], monthly["demand"])
    plt.xticks(rotation=45, ha="right")
    _fig(out / "02_monthly_demand.png", "Total demand by month")

    # 3. weekly pattern
    plt.figure(figsize=(7, 4))
    plt.bar(_CAL, [weekday.get(i, 0) for i in range(7)])
    _fig(out / "03_weekday_pattern.png", "Mean demand by weekday")

    # 4. top products
    top = by_product.head(top_n)
    plt.figure(figsize=(9, 4.5))
    plt.barh([label(p) for p in top.index][::-1], top.to_numpy()[::-1])
    _fig(out / "04_top_products.png", f"Top {top_n} products by total demand")

    # 5. demand distribution
    plt.figure(figsize=(8, 4))
    plt.hist(d["demand"], bins=50)
    _fig(out / "05_demand_distribution.png", "Distribution of daily series demand")

    # 6. product comparison (top 5 series over time)
    plt.figure(figsize=(10, 4.5))
    for pid in by_product.head(5).index:
        series = (
            d[d["product_id"] == pid]
            .groupby("date", as_index=False)["demand"]
            .sum()
        )
        plt.plot(series["date"], series["demand"], linewidth=0.8, label=label(pid))
    plt.legend(fontsize=8)
    _fig(out / "06_product_comparison.png", "Daily demand — top 5 products")

    (out / "eda_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
