"""Preprocessing tests: cleaning, gap filling, outlier strategies."""

import pandas as pd

from ml.config import load_config
from ml.data.preprocessing import get_series, preprocess


def _cfg(**outlier_overrides):
    cfg = load_config()
    if outlier_overrides:
        cfg["data"] = dict(cfg["data"])
        cfg["data"]["outliers"] = {
            **dict(cfg["data"]["outliers"]),
            **outlier_overrides,
        }
    return cfg


def _raw():
    return pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-05"],
            "product_id": ["P1"] * 4,
            "warehouse_id": ["W1"] * 4,
            "demand": [10.0, 5.0, 7.0, 20.0],
        }
    )


def test_duplicates_are_summed_and_gaps_filled():
    df, report = preprocess(_raw(), _cfg())
    # 2024-01-02 appears twice -> summed to 12
    day2 = df[df["date"] == pd.Timestamp("2024-01-02")]
    assert day2["demand"].tolist() == [12.0]
    # gap 01-03/01-04 filled with 0
    assert len(df) == 5
    assert df[df["date"] == pd.Timestamp("2024-01-03")]["demand"].tolist() == [0.0]
    assert report["merged_duplicate_rows"] == 1
    assert report["filled_missing_dates"] == 2


def test_invalid_dates_dropped_and_sorted():
    raw = _raw()
    raw.loc[0, "date"] = "garbage"
    df, report = preprocess(raw, _cfg())
    assert report["dropped_invalid_dates"] == 1
    assert df["date"].is_monotonic_increasing


def test_negative_demand_zeroed_by_default():
    raw = _raw()
    raw.loc[0, "demand"] = -4.0
    df, report = preprocess(raw, _cfg())
    assert report["negative_demand_rows"] == 1
    assert (df["demand"] >= 0).all()


def test_outlier_flagged_not_removed_by_default():
    raw = _raw()
    spike = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-06", periods=60, freq="D"),
            "product_id": ["P1"] * 60,
            "warehouse_id": ["W1"] * 60,
            "demand": [10.0] * 59 + [500.0],
        }
    )
    df, report = preprocess(pd.concat([raw, spike]), _cfg(strategy="flag"))
    assert report["outliers_detected"] >= 1
    assert df["demand"].max() == 500.0  # value untouched
    assert df.loc[df["demand"] == 500.0, "is_outlier"].all()


def test_outlier_remove_strategy():
    spike = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=60, freq="D"),
            "product_id": ["P1"] * 60,
            "warehouse_id": ["W1"] * 60,
            "demand": [10.0] * 59 + [500.0],
        }
    )
    df, report = preprocess(spike, _cfg(strategy="remove"))
    assert report["outliers_detected"] >= 1
    assert df["demand"].max() < 500.0


def test_get_series_aggregates_across_warehouses():
    raw = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01"],
            "product_id": ["P1", "P1"],
            "warehouse_id": ["W1", "W2"],
            "demand": [3.0, 4.0],
        }
    )
    df, _ = preprocess(raw, _cfg())
    series = get_series(df, "P1")  # product level: sum over warehouses
    assert series["demand"].tolist() == [7.0]
    w1 = get_series(df, "P1", "W1")
    assert w1["demand"].tolist() == [3.0]
