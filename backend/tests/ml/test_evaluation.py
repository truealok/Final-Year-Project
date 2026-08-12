"""Metric and chronological-split tests."""

import numpy as np
import pandas as pd
import pytest

from ml.modeling.evaluation import (
    evaluate,
    mae,
    r2,
    rmse,
    safe_mape,
    smape,
    time_series_split,
    wape,
)
from ml.modeling.selection import select_best


def test_mae_rmse_known_values():
    assert mae([10, 20], [12, 16]) == 3.0
    assert rmse([10, 20], [12, 16]) == pytest.approx(np.sqrt((4 + 16) / 2))


def test_safe_mape_excludes_zero_actuals():
    # zero actual would divide by zero — must be excluded, not fabricated
    value = safe_mape([0, 100], [5, 110])
    assert value == pytest.approx(10.0)  # only the 100->110 point counts


def test_safe_mape_all_zero_returns_none():
    assert safe_mape([0, 0], [1, 2]) is None


def test_smape_handles_double_zero():
    assert smape([0, 100], [0, 100]) == 0.0


def test_wape():
    assert wape([100, 100], [90, 110]) == pytest.approx(10.0)
    assert wape([0, 0], [1, 1]) is None


def test_r2_none_for_constant_actuals():
    assert r2([5, 5, 5], [5, 5, 5]) is None


def test_evaluate_bundle():
    out = evaluate([10, 20, 30], [12, 18, 33])
    assert set(out) == {"mae", "rmse", "mape", "smape", "wape", "r2"}
    assert out["mae"] == pytest.approx(7 / 3, abs=1e-3)


def test_empty_arrays_raise():
    with pytest.raises(ValueError):
        mae([], [])


def test_time_series_split_is_chronological():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=100, freq="D"),
            "demand": range(100),
        }
    )
    train, val, test = time_series_split(df, val_days=14, test_days=7)
    assert len(train) == 79 and len(val) == 14 and len(test) == 7
    # strict ordering, no overlap — random splitting is forbidden
    assert train["date"].max() < val["date"].min()
    assert val["date"].max() < test["date"].min()
    assert test["date"].max() == df["date"].max()


def test_time_series_split_no_test():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=50, freq="D"),
            "demand": range(50),
        }
    )
    train, val, test = time_series_split(df, val_days=10)
    assert len(train) == 40 and len(val) == 10 and test.empty


def test_select_best_prefers_lower_primary_metric():
    best, reason = select_best(
        {
            "prophet": {"wape": 8.0, "mae": 5.0},
            "xgboost": {"wape": 9.0, "mae": 4.0},
        }
    )
    assert best == "prophet"
    assert "wape" in reason


def test_select_best_tie_breaker_and_failures():
    best, _ = select_best(
        {
            "prophet": {"wape": 8.0, "mae": 6.0},
            "xgboost": {"wape": 8.0, "mae": 4.0},
        }
    )
    assert best == "xgboost"
    best, reason = select_best({"prophet": None, "xgboost": {"wape": 9.9, "mae": 1}})
    assert best == "xgboost"
    with pytest.raises(ValueError):
        select_best({"prophet": None})
