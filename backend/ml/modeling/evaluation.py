"""Time-series evaluation: chronological splits and error metrics.

Metric notes
------------
- **MAPE** divides by the actual value, so it explodes (or is undefined) when
  actuals are zero/near-zero. :func:`safe_mape` excludes those points and
  returns ``None`` when nothing remains — it never fabricates a number.
- **sMAPE** (0–200 %) and **WAPE** are reported alongside as zero-robust
  alternatives; WAPE is the default model-selection metric.
- **R²** is only reported when the actuals have non-zero variance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _as_arrays(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if a.shape != p.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {p.shape}")
    if a.size == 0:
        raise ValueError("Cannot evaluate empty arrays")
    return a, p


def mae(y_true, y_pred) -> float:
    a, p = _as_arrays(y_true, y_pred)
    return float(np.mean(np.abs(a - p)))


def rmse(y_true, y_pred) -> float:
    a, p = _as_arrays(y_true, y_pred)
    return float(np.sqrt(np.mean((a - p) ** 2)))


def safe_mape(y_true, y_pred, eps: float = 1e-6) -> float | None:
    """MAPE (%) over points with ``|actual| > eps``; ``None`` if none qualify."""
    a, p = _as_arrays(y_true, y_pred)
    mask = np.abs(a) > eps
    if not mask.any():
        return None
    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100)


def smape(y_true, y_pred) -> float:
    """Symmetric MAPE (%, 0–200). Points where both are 0 count as 0 error."""
    a, p = _as_arrays(y_true, y_pred)
    denom = np.abs(a) + np.abs(p)
    ratio = np.where(denom == 0, 0.0, np.abs(a - p) / np.where(denom == 0, 1, denom))
    return float(np.mean(ratio) * 200)


def wape(y_true, y_pred) -> float | None:
    """Weighted APE (%): ``sum|err| / sum|actual|``; ``None`` if actuals sum to 0."""
    a, p = _as_arrays(y_true, y_pred)
    denom = np.sum(np.abs(a))
    if denom == 0:
        return None
    return float(np.sum(np.abs(a - p)) / denom * 100)


def r2(y_true, y_pred) -> float | None:
    a, p = _as_arrays(y_true, y_pred)
    ss_tot = np.sum((a - a.mean()) ** 2)
    if ss_tot == 0:
        return None
    return float(1 - np.sum((a - p) ** 2) / ss_tot)


def evaluate(y_true, y_pred) -> dict[str, float | None]:
    """All metrics in one dict (values rounded for storage/display)."""

    def _round(v: float | None) -> float | None:
        return None if v is None else round(v, 4)

    return {
        "mae": _round(mae(y_true, y_pred)),
        "rmse": _round(rmse(y_true, y_pred)),
        "mape": _round(safe_mape(y_true, y_pred)),
        "smape": _round(smape(y_true, y_pred)),
        "wape": _round(wape(y_true, y_pred)),
        "r2": _round(r2(y_true, y_pred)),
    }


def time_series_split(
    series: pd.DataFrame, val_days: int, test_days: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Chronological train/validation/test split of one series by DATE.

    Never random: the last *test_days* dates form the test set, the
    *val_days* before them the validation set, everything earlier the train
    set. Empty frames are returned for zero-length windows.
    """
    df = series.sort_values("date").reset_index(drop=True)
    if val_days < 0 or test_days < 0:
        raise ValueError("val_days/test_days must be >= 0")
    last = df["date"].max()
    test_start = last - pd.Timedelta(days=test_days - 1) if test_days else None
    val_end = last - pd.Timedelta(days=test_days)
    val_start = val_end - pd.Timedelta(days=val_days - 1) if val_days else None

    test = df[df["date"] >= test_start] if test_days else df.iloc[0:0]
    val = (
        df[(df["date"] >= val_start) & (df["date"] <= val_end)]
        if val_days
        else df.iloc[0:0]
    )
    cutoff = val_start if val_days else (test_start if test_days else None)
    train = df if cutoff is None else df[df["date"] < cutoff]
    return (
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )
