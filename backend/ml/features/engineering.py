"""Time-series feature engineering for tree models (XGBoost).

Leakage rule: every feature for date *t* is computed **only** from values at
``t-1`` and earlier —

- lags use ``shift(k)`` with ``k >= 1``;
- rolling windows are computed on the series *shifted by one day*, so a
  ``rolling_mean_7`` at *t* covers ``t-7 .. t-1`` and never includes *t*.

Two construction paths share the same column definitions:

- :func:`make_supervised` — vectorised, builds the full training matrix;
- :func:`features_for_date` — builds the single feature row for one future
  date from a history series (used by recursive prediction).

``tests/ml/test_features.py`` asserts both paths produce identical values.
"""

from __future__ import annotations

from datetime import date as date_cls

import numpy as np
import pandas as pd

CALENDAR_FEATURES = [
    "year",
    "month",
    "week",
    "day_of_week",
    "day_of_month",
    "quarter",
    "is_weekend",
]


def feature_columns(
    lags: list[int], rolling_windows: list[int], rolling_std_windows: list[int]
) -> list[str]:
    """The canonical, ordered feature column list."""
    return (
        CALENDAR_FEATURES
        + [f"lag_{k}" for k in lags]
        + [f"rolling_mean_{w}" for w in rolling_windows]
        + [f"rolling_std_{w}" for w in rolling_std_windows]
    )


def _calendar(dates: pd.Series) -> pd.DataFrame:
    dt = dates.dt
    iso_week = dt.isocalendar().week.astype(int)
    return pd.DataFrame(
        {
            "year": dt.year.astype(int),
            "month": dt.month.astype(int),
            "week": iso_week,
            "day_of_week": dt.weekday.astype(int),
            "day_of_month": dt.day.astype(int),
            "quarter": dt.quarter.astype(int),
            "is_weekend": (dt.weekday >= 5).astype(int),
        },
        index=dates.index,
    )


def make_supervised(
    series: pd.DataFrame,
    lags: list[int],
    rolling_windows: list[int],
    rolling_std_windows: list[int],
    dropna: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Build the supervised frame for ONE series (columns: date, demand).

    Returns ``(frame, feature_cols)`` where *frame* has ``date``, ``demand``
    (the target) and every feature column. Rows in the warm-up period (where
    the longest lag/window is not yet available) are dropped when *dropna*.
    """
    df = series[["date", "demand"]].sort_values("date").reset_index(drop=True)
    out = pd.concat([df, _calendar(df["date"])], axis=1)

    y = df["demand"]
    shifted = y.shift(1)  # value at t-1: base for all windows
    for k in lags:
        out[f"lag_{k}"] = y.shift(k)
    for w in rolling_windows:
        out[f"rolling_mean_{w}"] = shifted.rolling(w, min_periods=w).mean()
    for w in rolling_std_windows:
        out[f"rolling_std_{w}"] = shifted.rolling(w, min_periods=w).std()

    cols = feature_columns(lags, rolling_windows, rolling_std_windows)
    if dropna:
        out = out.dropna(subset=cols).reset_index(drop=True)
    return out, cols


def features_for_date(
    history: pd.Series,
    target_date: pd.Timestamp | date_cls,
    lags: list[int],
    rolling_windows: list[int],
    rolling_std_windows: list[int],
) -> dict[str, float] | None:
    """Feature row for *target_date* given *history* (a date-indexed demand
    Series ending the day before *target_date* — earlier predictions included
    when forecasting recursively).

    Returns ``None`` when history is too short for the longest lag/window.
    """
    ts = pd.Timestamp(target_date)
    values = history.sort_index()
    needed = max(list(lags) + list(rolling_windows) + list(rolling_std_windows))
    if len(values) < needed:
        return None

    row: dict[str, float] = {
        "year": ts.year,
        "month": ts.month,
        "week": int(ts.isocalendar().week),
        "day_of_week": ts.weekday(),
        "day_of_month": ts.day,
        "quarter": ts.quarter,
        "is_weekend": int(ts.weekday() >= 5),
    }
    arr = values.to_numpy(dtype=float)
    for k in lags:
        # lag_k relative to target_date == the k-th most recent history value
        row[f"lag_{k}"] = float(arr[-k])
    for w in rolling_windows:
        row[f"rolling_mean_{w}"] = float(arr[-w:].mean())
    for w in rolling_std_windows:
        row[f"rolling_std_{w}"] = float(np.std(arr[-w:], ddof=1))
    return row
