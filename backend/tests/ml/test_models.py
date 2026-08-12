"""Model tests — Prophet and XGBoost fit/predict/persistence."""

import pandas as pd
import pytest

from ml.exceptions import InsufficientHistoryError
from ml.modeling.prophet_model import ProphetForecaster
from ml.modeling.xgboost_model import XGBForecaster

FUTURE = pd.date_range("2024-07-19", periods=14, freq="D")


def _fast_xgb(**kw):
    return XGBForecaster(
        lags=[1, 7],
        rolling_windows=[7],
        rolling_std_windows=[7],
        n_estimators=50,
        early_stopping_rounds=10,
        **kw,
    )


# --------------------------------------------------------------------- #
# XGBoost
# --------------------------------------------------------------------- #
def test_xgb_fit_and_recursive_predict(series_df):
    model = _fast_xgb().fit(series_df, eval_tail_days=14)
    pred = model.predict_recursive(series_df, FUTURE)
    assert list(pred.columns) == ["date", "yhat", "yhat_lower", "yhat_upper"]
    assert len(pred) == 14
    assert (pred["yhat"] >= 0).all()
    assert (pred["yhat_lower"] <= pred["yhat"]).all()
    assert (pred["yhat"] <= pred["yhat_upper"]).all()


def test_xgb_deterministic_given_seed(series_df):
    p1 = _fast_xgb(random_seed=1).fit(series_df).predict_recursive(
        series_df, FUTURE
    )
    p2 = _fast_xgb(random_seed=1).fit(series_df).predict_recursive(
        series_df, FUTURE
    )
    pd.testing.assert_frame_equal(p1, p2)


def test_xgb_insufficient_history_raises():
    tiny = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=20, freq="D"),
            "demand": range(20),
        }
    )
    with pytest.raises(InsufficientHistoryError):
        _fast_xgb().fit(tiny)


def test_xgb_save_load_roundtrip(series_df, tmp_path):
    model = _fast_xgb().fit(series_df)
    model.save(tmp_path / "xgb")
    loaded = XGBForecaster.load(tmp_path / "xgb")
    p1 = model.predict_recursive(series_df, FUTURE)
    p2 = loaded.predict_recursive(series_df, FUTURE)
    pd.testing.assert_frame_equal(p1, p2)


def test_xgb_predict_before_fit_raises(series_df):
    with pytest.raises(RuntimeError):
        _fast_xgb().predict_recursive(series_df, FUTURE)


# --------------------------------------------------------------------- #
# Prophet
# --------------------------------------------------------------------- #
def test_prophet_fit_predict_and_seasonality_policy(series_df):
    model = ProphetForecaster().fit(series_df)
    # 200 days of history: weekly on, yearly OFF (needs >= 730 by default)
    assert model.seasonalities_["weekly"] is True
    assert model.seasonalities_["yearly"] is False
    pred = model.predict(FUTURE)
    assert list(pred.columns) == ["date", "yhat", "yhat_lower", "yhat_upper"]
    assert len(pred) == 14
    assert (pred["yhat"] >= 0).all()
    assert (pred["yhat_lower"] <= pred["yhat"]).all()
    assert (pred["yhat"] <= pred["yhat_upper"]).all()


def test_prophet_save_load_roundtrip(series_df, tmp_path):
    model = ProphetForecaster().fit(series_df)
    model.save(tmp_path / "prophet")
    loaded = ProphetForecaster.load(tmp_path / "prophet")
    p1 = model.predict(FUTURE)
    p2 = loaded.predict(FUTURE)
    # yhat is deterministic; interval bounds are sampled by Prophet and
    # legitimately vary between predict calls — only sanity-check them.
    pd.testing.assert_series_equal(p1["yhat"], p2["yhat"], atol=1e-6)
    assert (p2["yhat_lower"] <= p2["yhat"]).all()
    assert (p2["yhat"] <= p2["yhat_upper"]).all()
    assert loaded.seasonalities_ == model.seasonalities_
