"""Feature-engineering tests — lag/rolling correctness and leakage prevention."""

import numpy as np
import pandas as pd

from ml.features.engineering import (
    feature_columns,
    features_for_date,
    make_supervised,
)

LAGS = [1, 7]
ROLL = [7]
ROLL_STD = [7]


def _series(n=60):
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n, freq="D"),
            "demand": np.arange(1.0, n + 1.0),  # 1, 2, 3, ... deterministic
        }
    )


def test_lag_values_are_previous_days():
    frame, _ = make_supervised(_series(), LAGS, ROLL, ROLL_STD)
    row = frame.iloc[0]  # first row after warm-up
    # demand on day t is t (1-indexed); lag_1 must equal t-1, lag_7 t-7
    assert row["lag_1"] == row["demand"] - 1
    assert row["lag_7"] == row["demand"] - 7


def test_rolling_excludes_current_day():
    """Leakage check: rolling_mean_7 at t covers t-7..t-1, never t."""
    frame, _ = make_supervised(_series(), LAGS, ROLL, ROLL_STD)
    row = frame.iloc[0]
    t = row["demand"]  # demand == day number
    expected = np.mean([t - k for k in range(1, 8)])  # previous 7 days
    assert row["rolling_mean_7"] == expected
    # if the current day leaked in, the mean would be higher:
    leaked = np.mean([t - k for k in range(0, 7)])
    assert row["rolling_mean_7"] != leaked


def test_warmup_rows_dropped():
    frame, _ = make_supervised(_series(), LAGS, ROLL, ROLL_STD)
    # longest lookback = 7 -> first 7 rows unusable
    assert len(frame) == 60 - 7
    assert not frame[feature_columns(LAGS, ROLL, ROLL_STD)].isna().any().any()


def test_single_row_builder_matches_vectorized():
    """features_for_date must produce EXACTLY the training-path values."""
    series = _series()
    frame, cols = make_supervised(series, LAGS, ROLL, ROLL_STD)
    for idx in [0, 10, len(frame) - 1]:
        row = frame.iloc[idx]
        history = (
            series[series["date"] < row["date"]]
            .set_index("date")["demand"]
        )
        single = features_for_date(history, row["date"], LAGS, ROLL, ROLL_STD)
        assert single is not None
        for col in cols:
            assert np.isclose(single[col], row[col]), (
                f"{col} mismatch at {row['date']}: "
                f"{single[col]} != {row[col]}"
            )


def test_features_for_date_requires_enough_history():
    series = _series(5)
    history = series.set_index("date")["demand"]
    assert (
        features_for_date(history, "2024-01-06", LAGS, ROLL, ROLL_STD) is None
    )


def test_calendar_features():
    frame, _ = make_supervised(_series(), LAGS, ROLL, ROLL_STD)
    sat = frame[frame["date"] == pd.Timestamp("2024-02-03")]  # a Saturday
    assert sat["day_of_week"].tolist() == [5]
    assert sat["is_weekend"].tolist() == [1]
    assert sat["month"].tolist() == [2]
    assert sat["quarter"].tolist() == [1]
