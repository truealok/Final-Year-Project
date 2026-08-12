"""Dataset validation tests."""

import pandas as pd
import pytest

from ml.data.validation import validate_dataset
from ml.exceptions import DataValidationError


def _frame(**overrides):
    base = {
        "date": pd.date_range("2024-01-01", periods=120, freq="D"),
        "product_id": ["P1"] * 120,
        "warehouse_id": ["W1"] * 120,
        "demand": [10.0] * 120,
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_valid_dataset_passes():
    report = validate_dataset(_frame(), min_history_days=90)
    assert report.is_valid
    assert report.rows == 120
    assert report.n_products == 1
    assert report.date_min == "2024-01-01"


def test_missing_required_columns_is_fatal():
    report = validate_dataset(pd.DataFrame({"date": [], "demand": []}))
    assert not report.is_valid
    assert "product_id" in report.errors[0]


def test_raise_on_error():
    with pytest.raises(DataValidationError):
        validate_dataset(pd.DataFrame({"x": [1]}), raise_on_error=True)


def test_empty_dataset_is_fatal():
    report = validate_dataset(_frame().iloc[0:0])
    assert not report.is_valid


def test_invalid_dates_counted():
    dates = [str(d.date()) for d in pd.date_range("2024-01-01", periods=120)]
    dates[:5] = ["not-a-date"] * 5
    report = validate_dataset(_frame(date=dates), min_history_days=90)
    assert report.invalid_dates == 5
    assert any("unparseable" in w for w in report.warnings)


def test_negative_and_zero_demand_flagged():
    df = _frame()
    df.loc[0, "demand"] = -5
    df.loc[1, "demand"] = 0
    report = validate_dataset(df, min_history_days=90)
    assert report.negative_demand == 1
    assert report.zero_demand_rows == 1
    assert report.is_valid  # warnings, not errors


def test_duplicates_counted_not_fatal():
    df = pd.concat([_frame(), _frame().head(3)], ignore_index=True)
    report = validate_dataset(df, min_history_days=90)
    assert report.duplicate_rows == 3
    assert report.is_valid


def test_all_series_below_min_history_is_fatal():
    report = validate_dataset(_frame(), min_history_days=365)
    assert not report.is_valid
    assert report.series_below_min_history[0]["days"] == 120


def test_some_series_below_min_history_is_warning():
    long = _frame()
    short = _frame(
        date=pd.date_range("2024-01-01", periods=120, freq="D"),
        product_id=["P2"] * 120,
    ).head(10)
    report = validate_dataset(
        pd.concat([long, short], ignore_index=True), min_history_days=90
    )
    assert report.is_valid
    assert len(report.series_below_min_history) == 1
