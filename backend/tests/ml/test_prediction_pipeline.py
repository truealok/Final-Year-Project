"""End-to-end pipeline tests: training -> registry -> predict_demand."""

import pandas as pd
import pytest

from ml.data.synthetic import generate_synthetic_demand
from ml.exceptions import ModelNotTrainedError
from ml.modeling.registry import ModelRegistry, make_series_key
from ml.pipeline import prediction
from ml.pipeline.training import train_all


@pytest.fixture()
def trained_env(tmp_path, ml_cfg):
    """Synthetic CSV dataset + one trained (xgboost) product in tmp dirs."""
    csv_path = tmp_path / "synthetic.csv"
    generate_synthetic_demand(
        n_products=1, n_warehouses=2, days=220, seed=11
    ).to_csv(csv_path, index=False)

    ml_cfg["data"] = dict(ml_cfg["data"])
    ml_cfg["data"]["source"] = "csv"
    ml_cfg["data"]["csv_path"] = str(csv_path)
    # keep the test fast: shrink xgboost
    ml_cfg["models"] = {
        "prophet": dict(ml_cfg["models"]["prophet"]),
        "xgboost": {
            **dict(ml_cfg["models"]["xgboost"]),
            "n_estimators": 60,
            "early_stopping_rounds": 10,
        },
    }
    prediction.clear_model_cache()
    report = train_all(ml_cfg, product_ids=["SYN-P001"], models=["xgboost"])
    return ml_cfg, report


def test_train_all_produces_real_metrics(trained_env):
    _, report = trained_env
    assert len(report["trained"]) == 1
    rec = report["trained"][0]
    assert rec["best_model"] == "xgboost"
    metrics = rec["metrics"]["xgboost"]
    # metrics must come from actual evaluation — sane, finite values
    assert metrics["mae"] > 0
    assert metrics["rmse"] >= metrics["mae"]
    assert 0 < metrics["wape"] < 100


def test_registry_layout_and_best(trained_env, tmp_path):
    cfg, _ = trained_env
    registry = ModelRegistry(
        cfg["paths"]["models_dir"], cfg["paths"]["artifacts_dir"]
    )
    key = make_series_key("SYN-P001")
    assert registry.has_series(key)
    best = registry.best_info(key)
    assert best["model_type"] == "xgboost"
    assert best["version"] == 1
    model, meta = registry.load(key)
    assert meta["metrics"]["mae"] > 0
    assert meta["series_level"] == "product"


def test_predict_demand_output_contract(trained_env):
    cfg, _ = trained_env
    result = prediction.predict_demand("SYN-P001", forecast_days=10, cfg=cfg)
    assert result["product_id"] == "SYN-P001"
    assert result["warehouse_id"] is None  # product-level: never fabricated
    assert result["series_level"] == "product"
    assert result["model"] == "XGBoost"
    assert len(result["forecast"]) == 10
    point = result["forecast"][0]
    assert set(point) == {
        "date", "predicted_demand", "lower_bound", "upper_bound"
    }
    assert point["lower_bound"] <= point["predicted_demand"] <= point["upper_bound"]
    # forecast starts right after the observed history
    assert point["date"] > "2024-01-01"


def test_predict_demand_warehouse_falls_back_to_product(trained_env):
    """No product x warehouse model trained -> product model + explicit flag."""
    cfg, _ = trained_env
    result = prediction.predict_demand(
        "SYN-P001", warehouse_id="SYN-W01", forecast_days=5, cfg=cfg
    )
    assert result["series_level"] == "product"
    assert result["warehouse_id"] is None
    assert result["requested_warehouse_id"] == "SYN-W01"


def test_predict_demand_unknown_product_raises(trained_env):
    cfg, _ = trained_env
    with pytest.raises(ModelNotTrainedError):
        prediction.predict_demand("NO-SUCH-PRODUCT", forecast_days=5, cfg=cfg)


def test_predict_demand_untrained_model_type_raises(trained_env):
    cfg, _ = trained_env
    with pytest.raises(ModelNotTrainedError):
        prediction.predict_demand(
            "SYN-P001", model_type="prophet", forecast_days=5, cfg=cfg
        )


def test_experiment_log_written(trained_env):
    cfg, _ = trained_env
    log = (
        pd.read_json(
            f"{cfg['paths']['artifacts_dir']}/evaluation/experiments.jsonl",
            lines=True,
        )
    )
    assert len(log) == 1
    assert log.iloc[0]["model"] == "xgboost"
    assert log.iloc[0]["mae"] > 0
