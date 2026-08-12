"""Fixtures for the ML test suite (pure sync — no FastAPI/DB involved)."""

import pandas as pd
import pytest

from ml.config import load_config
from ml.data.synthetic import generate_synthetic_demand


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    """One product, one warehouse, 200 days — small but structured."""
    return generate_synthetic_demand(
        n_products=1, n_warehouses=1, days=200, seed=7
    )


@pytest.fixture()
def series_df(synthetic_df) -> pd.DataFrame:
    """A single (date, demand) series frame."""
    return (
        synthetic_df.groupby("date", as_index=False)["demand"]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )


@pytest.fixture()
def ml_cfg(tmp_path):
    """Default config with model/artifact paths redirected to tmp."""
    cfg = load_config()
    cfg["paths"] = {
        "models_dir": str(tmp_path / "models"),
        "artifacts_dir": str(tmp_path / "artifacts"),
    }
    return cfg
