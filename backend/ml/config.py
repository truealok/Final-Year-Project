"""ML configuration loading.

``load_config()`` reads ``ml/config.yaml`` (or an explicit path / the
``ML_CONFIG`` environment variable), deep-merges it over built-in defaults and
returns an attribute-accessible mapping. Relative paths resolve against the
``backend/`` directory so CLI runs (``python -m ml.train``) and backend
imports both work.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

from ml.exceptions import ConfigError

# backend/ directory (parent of the ml package)
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

_DEFAULTS: dict[str, Any] = {
    "random_seed": 42,
    "data": {
        "source": "sqlite",
        "sqlite_path": "dev.db",
        "csv_path": None,
        "min_history_days": 90,
        "fill_missing_dates": True,
        "fill_value": 0.0,
        "negative_strategy": "zero",
        "outliers": {
            "method": "iqr",
            "strategy": "flag",
            "iqr_multiplier": 3.0,
            "zscore_threshold": 4.0,
        },
    },
    "series": {"level": "auto", "min_warehouse_history_days": 90},
    "forecast": {"horizon_days": 30, "confidence_level": 0.95},
    "validation": {"val_days": 28, "test_days": 0},
    "features": {
        "lags": [1, 7, 14, 28],
        "rolling_windows": [7, 14, 28],
        "rolling_std_windows": [7, 28],
    },
    "models": {
        "prophet": {
            "weekly_seasonality": "auto",
            "yearly_seasonality": "auto",
            "yearly_min_days": 730,
            "daily_seasonality": False,
            "interval_width": 0.95,
        },
        "xgboost": {
            "n_estimators": 400,
            "learning_rate": 0.05,
            "max_depth": 5,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "min_child_weight": 3.0,
            "early_stopping_rounds": 40,
        },
    },
    "selection": {"primary_metric": "wape", "tie_breaker": "mae"},
    "batch": {"max_series": 10},
    "paths": {"models_dir": "ml/models", "artifacts_dir": "ml/artifacts"},
}


class ConfigDict(dict):
    """Read-only-ish dict with attribute access: ``cfg.data.source``."""

    def __getattr__(self, name: str) -> Any:
        try:
            value = self[name]
        except KeyError as exc:  # pragma: no cover - programming error
            raise AttributeError(name) from exc
        return ConfigDict(value) if isinstance(value, dict) else value


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(path: str | Path | None = None) -> ConfigDict:
    """Load config from *path*, ``$ML_CONFIG`` or the packaged default."""
    cfg_path = Path(path or os.environ.get("ML_CONFIG") or DEFAULT_CONFIG_PATH)
    file_cfg: dict[str, Any] = {}
    if cfg_path.exists():
        try:
            file_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {cfg_path}: {exc}") from exc
        if not isinstance(file_cfg, dict):
            raise ConfigError(f"{cfg_path} must contain a YAML mapping")
    elif path is not None:
        raise ConfigError(f"Config file not found: {cfg_path}")
    return ConfigDict(_deep_merge(_DEFAULTS, file_cfg))


def resolve_path(value: str | Path) -> Path:
    """Resolve a (possibly relative) configured path against backend/."""
    p = Path(value)
    return p if p.is_absolute() else BACKEND_DIR / p
