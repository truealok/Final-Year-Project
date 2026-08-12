"""Training pipeline.

Per series: chronological split → fit Prophet and XGBoost on TRAIN only →
evaluate both on the SAME held-out validation window → pick the winner →
refit both on train+validation for deployment → persist to the registry
with real validation metrics + explainability artifacts → log experiments.

Both models are persisted (not just the winner) because the public API lets
the caller request a specific model type; ``best.json`` records the winner
for default routing.
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from ml.config import ConfigDict, load_config, resolve_path
from ml.data.preprocessing import get_series
from ml.exceptions import InsufficientHistoryError, MLError
from ml.features.engineering import make_supervised
from ml.modeling.evaluation import evaluate, time_series_split
from ml.modeling.prophet_model import ProphetForecaster
from ml.modeling.registry import ModelRegistry, make_series_key
from ml.modeling.selection import select_best
from ml.modeling.xgboost_model import XGBForecaster
from ml.pipeline.dataset import dataset_fingerprint, dataset_source_id, load_dataset


def _build_prophet(cfg: ConfigDict) -> ProphetForecaster:
    p = cfg.models.prophet
    return ProphetForecaster(
        weekly_seasonality=p.weekly_seasonality,
        yearly_seasonality=p.yearly_seasonality,
        yearly_min_days=int(p.yearly_min_days),
        daily_seasonality=bool(p.daily_seasonality),
        interval_width=float(p.interval_width),
    )


def _build_xgb(cfg: ConfigDict) -> XGBForecaster:
    x = cfg.models.xgboost
    f = cfg.features
    return XGBForecaster(
        lags=list(f.lags),
        rolling_windows=list(f.rolling_windows),
        rolling_std_windows=list(f.rolling_std_windows),
        n_estimators=int(x.n_estimators),
        learning_rate=float(x.learning_rate),
        max_depth=int(x.max_depth),
        subsample=float(x.subsample),
        colsample_bytree=float(x.colsample_bytree),
        min_child_weight=float(x.min_child_weight),
        early_stopping_rounds=int(x.early_stopping_rounds),
        confidence_level=float(cfg.forecast.confidence_level),
        random_seed=int(cfg.random_seed),
    )


def train_series(
    df: pd.DataFrame,
    product_id: str,
    warehouse_id: str | None,
    cfg: ConfigDict,
    registry: ModelRegistry,
    models: list[str] | None = None,
    dataset_version: str | None = None,
) -> dict[str, Any]:
    """Train the requested models for one series and register the winner.

    Returns a result record with per-model validation metrics, the selected
    best model and any per-model failures. Raises
    :class:`InsufficientHistoryError` when the series itself is too short.
    """
    models = models or ["prophet", "xgboost"]
    series = get_series(df, product_id, warehouse_id)
    series_key = make_series_key(product_id, warehouse_id)

    min_days = int(cfg.data.min_history_days)
    if len(series) < min_days:
        raise InsufficientHistoryError(
            f"Series {series_key} has {len(series)} days; needs >= {min_days}"
        )

    val_days = int(cfg.validation.val_days)
    test_days = int(cfg.validation.test_days)
    train, val, test = time_series_split(series, val_days, test_days)
    if val.empty:
        raise InsufficientHistoryError(
            f"Validation window is empty for {series_key} "
            f"(val_days={val_days})"
        )
    val_dates = pd.DatetimeIndex(val["date"])
    y_val = val["demand"].to_numpy(dtype=float)

    fitted: dict[str, Any] = {}
    metrics_by_model: dict[str, dict[str, Any] | None] = {}
    errors: dict[str, str] = {}
    durations: dict[str, float] = {}

    for name in models:
        started = time.perf_counter()
        try:
            if name == "prophet":
                model = _build_prophet(cfg).fit(train)
                pred = model.predict(val_dates)
            elif name == "xgboost":
                model = _build_xgb(cfg).fit(train, eval_tail_days=val_days)
                pred = model.predict_recursive(train, val_dates)
            else:
                errors[name] = f"unknown model '{name}'"
                metrics_by_model[name] = None
                continue
            metrics_by_model[name] = evaluate(y_val, pred["yhat"].to_numpy())
            fitted[name] = model
        except MLError as exc:
            errors[name] = str(exc)
            metrics_by_model[name] = None
        except Exception as exc:  # keep one bad model from killing the batch
            errors[name] = f"{type(exc).__name__}: {exc}"
            metrics_by_model[name] = None
        durations[name] = time.perf_counter() - started

    best_name, reason = select_best(
        metrics_by_model,
        primary_metric=cfg.selection.primary_metric,
        tie_breaker=cfg.selection.tie_breaker,
    )

    # ---- deploy: refit every successful model on train + validation ---- #
    deploy = pd.concat([train, val], ignore_index=True)
    val_window = [str(val["date"].min().date()), str(val["date"].max().date())]
    artifacts_dir = resolve_path(cfg.paths.artifacts_dir)
    versions: dict[str, int] = {}
    for name, _ in list(fitted.items()):
        refit_started = time.perf_counter()
        if name == "prophet":
            deployed = _build_prophet(cfg).fit(deploy)
        else:
            deployed = _build_xgb(cfg).fit(deploy, eval_tail_days=val_days)
        durations[name] += time.perf_counter() - refit_started

        metadata = {
            "series_key": series_key,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "series_level": "product_warehouse" if warehouse_id else "product",
            "dataset": dataset_source_id(cfg),
            "dataset_version": dataset_version,
            "training_rows": int(len(deploy)),
            "history_start": str(series["date"].min().date()),
            "history_end": str(series["date"].max().date()),
            "validation_window": val_window,
            "metrics_source": "held-out validation window (chronological)",
            "forecast_horizon_days": int(cfg.forecast.horizon_days),
            "confidence_level": float(cfg.forecast.confidence_level),
        }
        version, target_dir = registry.save_model(
            series_key, name, deployed, metrics_by_model[name], metadata
        )
        versions[name] = version
        fitted[name] = deployed

        registry.log_experiment(
            dataset=dataset_source_id(cfg),
            series_key=series_key,
            product_id=product_id,
            warehouse_id=warehouse_id,
            model=name,
            version=version,
            parameters=(
                deployed.params
                if isinstance(deployed, XGBForecaster)
                else deployed.seasonalities_
            ),
            metrics=metrics_by_model[name] or {},
            training_seconds=durations[name],
        )

        # Explainability artifacts (from the actually deployed models).
        try:
            if name == "xgboost":
                from ml.explain.shap_explain import explain_xgboost

                frame, _ = make_supervised(
                    deploy,
                    deployed.lags,
                    deployed.rolling_windows,
                    deployed.rolling_std_windows,
                )
                explain_xgboost(
                    deployed, frame, artifacts_dir / "shap" / series_key
                )
            elif name == "prophet":
                from ml.explain.shap_explain import prophet_components

                prophet_components(
                    deployed,
                    pd.DatetimeIndex(series["date"]),
                    artifacts_dir / "shap" / series_key,
                )
        except Exception as exc:  # artifacts are best-effort
            errors[f"{name}_explain"] = f"{type(exc).__name__}: {exc}"

    registry.set_best(
        series_key,
        best_name,
        versions[best_name],
        reason,
        metrics_by_model[best_name] or {},
        metadata={
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "series_level": "product_warehouse" if warehouse_id else "product",
            "validation_window": val_window,
        },
    )

    result: dict[str, Any] = {
        "series_key": series_key,
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "history_days": int(len(series)),
        "validation_window": val_window,
        "metrics": metrics_by_model,
        "best_model": best_name,
        "selection_reason": reason,
        "versions": versions,
        "errors": errors,
    }
    if test_days and not test.empty:
        # Optional untouched test window, evaluated with the winner only.
        best_model = fitted[best_name]
        test_dates = pd.DatetimeIndex(test["date"])
        pred = (
            best_model.predict(test_dates)
            if best_name == "prophet"
            else best_model.predict_recursive(deploy, test_dates)
        )
        result["test_metrics"] = evaluate(
            test["demand"].to_numpy(dtype=float), pred["yhat"].to_numpy()
        )
    return result


def train_all(
    cfg: ConfigDict | None = None,
    *,
    product_ids: list[str] | None = None,
    warehouse_id: str | None = None,
    models: list[str] | None = None,
    max_series: int | None = None,
) -> dict[str, Any]:
    """Train models for many series; returns a batch report.

    Without *product_ids*, products are ranked by total demand and capped at
    ``batch.max_series`` (never train thousands of models by accident).
    """
    cfg = cfg or load_config()
    df, validation, pre_report = load_dataset(cfg)
    if validation is not None and not validation.is_valid:
        raise MLError(
            "Dataset failed validation: " + "; ".join(validation.errors)
        )
    fingerprint = dataset_fingerprint(df)

    registry = ModelRegistry(
        resolve_path(cfg.paths.models_dir), resolve_path(cfg.paths.artifacts_dir)
    )

    if product_ids is None:
        ranked = (
            df.groupby("product_id")["demand"].sum().sort_values(ascending=False)
        )
        cap = max_series if max_series is not None else int(cfg.batch.max_series)
        product_ids = list(ranked.index[:cap])
    elif max_series is not None:
        product_ids = product_ids[:max_series]

    results: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for pid in product_ids:
        try:
            results.append(
                train_series(
                    df,
                    pid,
                    warehouse_id,
                    cfg,
                    registry,
                    models=models,
                    dataset_version=fingerprint,
                )
            )
        except MLError as exc:
            skipped.append({"product_id": pid, "reason": str(exc)})

    return {
        "dataset": dataset_source_id(cfg),
        "dataset_version": fingerprint,
        "validation_report": validation.to_dict() if validation else None,
        "preprocess_report": pre_report,
        "trained": results,
        "skipped": skipped,
    }
