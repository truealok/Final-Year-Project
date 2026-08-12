"""SHAP explainability tests."""

from ml.explain.shap_explain import explain_xgboost
from ml.features.engineering import make_supervised
from ml.modeling.xgboost_model import XGBForecaster

LAGS = [1, 7]
ROLL = [7]
ROLL_STD = [7]


def test_shap_importance_from_trained_model(series_df, tmp_path):
    model = XGBForecaster(
        lags=LAGS,
        rolling_windows=ROLL,
        rolling_std_windows=ROLL_STD,
        n_estimators=50,
        early_stopping_rounds=10,
    ).fit(series_df)
    frame, _ = make_supervised(series_df, LAGS, ROLL, ROLL_STD)

    report = explain_xgboost(model, frame, tmp_path / "shap")

    # every model feature gets a real importance value
    assert set(report["feature_importance"]) == set(model.feature_cols)
    assert all(v >= 0 for v in report["feature_importance"].values())
    assert report["n_rows_explained"] == len(frame)
    # signed views are subsets of the feature set
    assert set(report["top_positive_features"]) <= set(model.feature_cols)
    assert set(report["top_negative_features"]) <= set(model.feature_cols)
    # artifacts written
    assert (tmp_path / "shap" / "feature_importance.json").exists()
    assert (tmp_path / "shap" / "shap_summary.png").exists()


def test_shap_importance_is_nontrivial(series_df, tmp_path):
    """On autocorrelated demand, lag/rolling features must carry signal."""
    model = XGBForecaster(
        lags=LAGS,
        rolling_windows=ROLL,
        rolling_std_windows=ROLL_STD,
        n_estimators=50,
        early_stopping_rounds=10,
    ).fit(series_df)
    frame, _ = make_supervised(series_df, LAGS, ROLL, ROLL_STD)
    report = explain_xgboost(model, frame)
    total = sum(report["feature_importance"].values())
    assert total > 0
    history_features = {"lag_1", "lag_7", "rolling_mean_7", "rolling_std_7"}
    history_share = (
        sum(report["feature_importance"][f] for f in history_features) / total
    )
    assert history_share > 0.3
