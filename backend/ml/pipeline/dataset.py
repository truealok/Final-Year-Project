"""Dataset assembly shared by training, prediction, EDA and the CLI."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import pandas as pd

from ml.config import ConfigDict, resolve_path
from ml.data.loaders import aggregate_daily, load_raw
from ml.data.preprocessing import preprocess
from ml.data.validation import ValidationReport, validate_dataset

# Small cache so API predictions do not re-read the dataset on every call.
_CACHE: dict[str, tuple[float, float, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 60.0


def dataset_source_id(cfg: ConfigDict) -> str:
    """Stable identifier of the configured data source (for logs/metadata)."""
    if cfg.data.source == "csv":
        return f"csv:{cfg.data.csv_path}"
    return f"sqlite:{cfg.data.sqlite_path}"


def dataset_fingerprint(df: pd.DataFrame) -> str:
    """Cheap content fingerprint used as ``dataset_version`` in metadata."""
    basis = (
        f"{len(df)}|{df['date'].min()}|{df['date'].max()}|"
        f"{float(df['demand'].sum()):.2f}|{df['product_id'].nunique()}"
    )
    return hashlib.md5(basis.encode()).hexdigest()[:12]


def load_dataset(
    cfg: ConfigDict,
    *,
    validate: bool = True,
    use_cache: bool = False,
) -> tuple[pd.DataFrame, ValidationReport | None, dict[str, Any]]:
    """Load → aggregate (both levels) → preprocess.

    Returns ``(df, validation_report, preprocess_report)`` where *df* is the
    preprocessed frame at **product × warehouse** granularity; product-level
    series are derived on demand by summing (see
    :func:`ml.data.preprocessing.get_series`).
    """
    source = dataset_source_id(cfg)
    now = time.monotonic()

    mtime = 0.0
    path = resolve_path(
        cfg.data.csv_path if cfg.data.source == "csv" else cfg.data.sqlite_path
    )
    if Path(path).exists():
        mtime = Path(path).stat().st_mtime

    if use_cache:
        cached = _CACHE.get(source)
        if cached and cached[0] == mtime and now - cached[1] < _CACHE_TTL_SECONDS:
            return cached[2], None, {}

    raw = load_raw(cfg)
    agg = aggregate_daily(raw, by_warehouse=True)

    report = None
    if validate:
        report = validate_dataset(
            agg, min_history_days=int(cfg.data.min_history_days)
        )

    df, pre_report = preprocess(agg, cfg)

    if use_cache:
        _CACHE[source] = (mtime, now, df)
    return df, report, pre_report


def clear_cache() -> None:
    _CACHE.clear()
