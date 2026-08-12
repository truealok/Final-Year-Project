"""Versioned model registry + experiment log.

Layout under ``ml/models/`` (configurable)::

    <series_key>/
        prophet/
            v1/  model.json, prophet_meta.json, metadata.json
            v2/  ...
        xgboost/
            v1/  model.ubj, xgb_meta.json, metadata.json
        best.json            # {"model_type", "version", "reason", ...}

``series_key`` is filesystem-safe: ``p_<product_id>`` or
``p_<product_id>__w_<warehouse_id>``.

Every ``save`` also appends one line to the experiment registry
(``ml/artifacts/evaluation/experiments.jsonl`` + a mirrored ``.csv``) with
the metrics that came out of the actual evaluation run.
"""

from __future__ import annotations

import csv
import json
import re
import uuid as uuid_lib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml.exceptions import ModelNotTrainedError
from ml.modeling.prophet_model import ProphetForecaster
from ml.modeling.xgboost_model import XGBForecaster

_LOADERS = {"prophet": ProphetForecaster.load, "xgboost": XGBForecaster.load}

_EXPERIMENT_FIELDS = [
    "experiment_id",
    "timestamp",
    "dataset",
    "series_key",
    "product_id",
    "warehouse_id",
    "model",
    "version",
    "parameters",
    "mae",
    "rmse",
    "mape",
    "smape",
    "wape",
    "training_seconds",
]


def make_series_key(product_id: str, warehouse_id: str | None = None) -> str:
    key = f"p_{product_id}"
    if warehouse_id:
        key += f"__w_{warehouse_id}"
    return re.sub(r"[^A-Za-z0-9_\-]", "-", key)


class ModelRegistry:
    def __init__(self, models_dir: str | Path, artifacts_dir: str | Path) -> None:
        self.root = Path(models_dir)
        self.artifacts = Path(artifacts_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Saving
    # ------------------------------------------------------------------ #
    def next_version(self, series_key: str, model_type: str) -> int:
        base = self.root / series_key / model_type
        if not base.exists():
            return 1
        versions = [
            int(p.name[1:])
            for p in base.iterdir()
            if p.is_dir() and re.fullmatch(r"v\d+", p.name)
        ]
        return max(versions, default=0) + 1

    def save_model(
        self,
        series_key: str,
        model_type: str,
        model: ProphetForecaster | XGBForecaster,
        metrics: dict[str, Any],
        metadata: dict[str, Any],
    ) -> tuple[int, Path]:
        """Persist a trained model as the next version; returns (version, dir)."""
        version = self.next_version(series_key, model_type)
        target = self.root / series_key / model_type / f"v{version}"
        model.save(target)
        full_meta = {
            **metadata,
            "model_type": model_type,
            "version": version,
            "metrics": metrics,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        (target / "metadata.json").write_text(
            json.dumps(full_meta, indent=2, default=str), encoding="utf-8"
        )
        return version, target

    def set_best(
        self,
        series_key: str,
        model_type: str,
        version: int,
        reason: str,
        metrics: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "model_type": model_type,
            "version": version,
            "reason": reason,
            "metrics": metrics,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        (self.root / series_key / "best.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #
    def has_series(self, series_key: str) -> bool:
        return (self.root / series_key / "best.json").exists()

    def best_info(self, series_key: str) -> dict[str, Any]:
        path = self.root / series_key / "best.json"
        if not path.exists():
            raise ModelNotTrainedError(
                f"No trained model for series '{series_key}'. "
                "Run `python -m ml.train` first."
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def load(
        self,
        series_key: str,
        model_type: str | None = None,
        version: int | None = None,
    ) -> tuple[ProphetForecaster | XGBForecaster, dict[str, Any]]:
        """Load (model, metadata). Defaults to the best model, latest version."""
        if model_type is None:
            best = self.best_info(series_key)
            model_type = best["model_type"]
            version = version or best["version"]
        if model_type not in _LOADERS:
            raise ModelNotTrainedError(f"Unknown model type '{model_type}'")
        base = self.root / series_key / model_type
        if version is None:
            if not base.exists():
                raise ModelNotTrainedError(
                    f"No trained {model_type} model for series '{series_key}'"
                )
            versions = [
                int(p.name[1:])
                for p in base.iterdir()
                if p.is_dir() and re.fullmatch(r"v\d+", p.name)
            ]
            if not versions:
                raise ModelNotTrainedError(
                    f"No trained {model_type} model for series '{series_key}'"
                )
            version = max(versions)
        target = base / f"v{version}"
        if not target.exists():
            raise ModelNotTrainedError(
                f"{model_type} v{version} not found for series '{series_key}'"
            )
        metadata = json.loads(
            (target / "metadata.json").read_text(encoding="utf-8")
        )
        return _LOADERS[model_type](target), metadata

    # ------------------------------------------------------------------ #
    # Introspection (for the backend /forecast/models endpoint & CLI)
    # ------------------------------------------------------------------ #
    def list_series(self) -> list[str]:
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and (p / "best.json").exists()
        )

    def summary(self) -> dict[str, Any]:
        """Aggregate stats per model type across all trained series."""
        per_type: dict[str, dict[str, Any]] = {}
        for series_key in self.list_series():
            best = self.best_info(series_key)
            for model_type in _LOADERS:
                type_dir = self.root / series_key / model_type
                if not type_dir.exists():
                    continue
                versions = [
                    p for p in type_dir.iterdir()
                    if p.is_dir() and re.fullmatch(r"v\d+", p.name)
                ]
                if not versions:
                    continue
                latest = max(versions, key=lambda p: int(p.name[1:]))
                meta_path = latest / "metadata.json"
                if not meta_path.exists():
                    continue
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                bucket = per_type.setdefault(
                    model_type,
                    {"n_series": 0, "n_best": 0, "metrics": [], "last_trained": None},
                )
                bucket["n_series"] += 1
                if best.get("model_type") == model_type:
                    bucket["n_best"] += 1
                bucket["metrics"].append(meta.get("metrics", {}))
                saved = meta.get("saved_at")
                if saved and (
                    bucket["last_trained"] is None or saved > bucket["last_trained"]
                ):
                    bucket["last_trained"] = saved

        out: dict[str, Any] = {}
        for model_type, bucket in per_type.items():
            avg: dict[str, float] = {}
            for name in ("mae", "rmse", "mape", "smape", "wape"):
                vals = [
                    m[name]
                    for m in bucket["metrics"]
                    if m.get(name) is not None
                ]
                if vals:
                    avg[name] = round(sum(vals) / len(vals), 2)
            out[model_type] = {
                "n_series": bucket["n_series"],
                "n_best": bucket["n_best"],
                "avg_metrics": avg,
                "last_trained": bucket["last_trained"],
            }
        return out

    # ------------------------------------------------------------------ #
    # Experiment log
    # ------------------------------------------------------------------ #
    def log_experiment(
        self,
        *,
        dataset: str,
        series_key: str,
        product_id: str,
        warehouse_id: str | None,
        model: str,
        version: int,
        parameters: dict[str, Any],
        metrics: dict[str, Any],
        training_seconds: float,
    ) -> str:
        exp_dir = self.artifacts / "evaluation"
        exp_dir.mkdir(parents=True, exist_ok=True)
        experiment_id = uuid_lib.uuid4().hex[:12]
        record = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset": dataset,
            "series_key": series_key,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "model": model,
            "version": version,
            "parameters": json.dumps(parameters, default=str),
            "mae": metrics.get("mae"),
            "rmse": metrics.get("rmse"),
            "mape": metrics.get("mape"),
            "smape": metrics.get("smape"),
            "wape": metrics.get("wape"),
            "training_seconds": round(training_seconds, 2),
        }
        with (exp_dir / "experiments.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
        csv_path = exp_dir / "experiments.csv"
        write_header = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_EXPERIMENT_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(record)
        return experiment_id
