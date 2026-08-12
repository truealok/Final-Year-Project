"""Prophet forecaster.

Wraps ``prophet.Prophet`` behind the small interface the pipeline uses:
``fit(series)``, ``predict(dates)``, ``save(dir)`` / ``load(dir)``.

Seasonality policy (honest by construction):

- weekly: on when the training span covers >= 14 days (else off);
- yearly: on **only** when the span covers ``yearly_min_days`` (default 730 —
  with a single observed cycle, yearly seasonality cannot be separated from
  trend and would overfit);
- daily: off (data is daily, sub-daily seasonality does not exist).

Prediction intervals come from Prophet itself (``interval_width``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

MODEL_TYPE = "prophet"
_MODEL_FILE = "model.json"
_META_FILE = "prophet_meta.json"

# cmdstanpy is extremely chatty at INFO level during every fit.
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)


class ProphetForecaster:
    def __init__(
        self,
        weekly_seasonality: bool | str = "auto",
        yearly_seasonality: bool | str = "auto",
        yearly_min_days: int = 730,
        daily_seasonality: bool = False,
        interval_width: float = 0.95,
    ) -> None:
        self.weekly_seasonality = weekly_seasonality
        self.yearly_seasonality = yearly_seasonality
        self.yearly_min_days = yearly_min_days
        self.daily_seasonality = daily_seasonality
        self.interval_width = interval_width
        self.model = None
        self.seasonalities_: dict[str, bool] = {}

    # ------------------------------------------------------------------ #
    def fit(self, series: pd.DataFrame) -> "ProphetForecaster":
        """Fit on a series frame with columns ``date`` and ``demand``."""
        from prophet import Prophet  # deferred: heavy import

        train = (
            series[["date", "demand"]]
            .rename(columns={"date": "ds", "demand": "y"})
            .sort_values("ds")
            .reset_index(drop=True)
        )
        span_days = (train["ds"].max() - train["ds"].min()).days + 1

        weekly = (
            span_days >= 14
            if self.weekly_seasonality == "auto"
            else bool(self.weekly_seasonality)
        )
        yearly = (
            span_days >= self.yearly_min_days
            if self.yearly_seasonality == "auto"
            else bool(self.yearly_seasonality)
        )
        self.seasonalities_ = {"weekly": weekly, "yearly": yearly, "daily": False}

        self.model = Prophet(
            weekly_seasonality=weekly,
            yearly_seasonality=yearly,
            daily_seasonality=self.daily_seasonality,
            interval_width=self.interval_width,
        )
        self.model.fit(train)
        return self

    def predict(self, dates: pd.DatetimeIndex | list) -> pd.DataFrame:
        """Forecast the given dates → columns date, yhat, yhat_lower, yhat_upper.

        Negative predictions are floored at 0 (demand cannot be negative).
        """
        if self.model is None:
            raise RuntimeError("ProphetForecaster.predict called before fit/load")
        future = pd.DataFrame({"ds": pd.DatetimeIndex(dates)})
        fcst = self.model.predict(future)
        out = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
            columns={"ds": "date"}
        )
        for col in ("yhat", "yhat_lower", "yhat_upper"):
            out[col] = out[col].clip(lower=0.0)
        # bounds can invert after clipping degenerate cases; enforce ordering
        out["yhat_lower"] = out[["yhat_lower", "yhat"]].min(axis=1)
        out["yhat_upper"] = out[["yhat_upper", "yhat"]].max(axis=1)
        return out

    def components(self, dates: pd.DatetimeIndex | list) -> pd.DataFrame:
        """Native decomposition (trend / weekly / yearly) for explainability."""
        if self.model is None:
            raise RuntimeError("ProphetForecaster.components called before fit")
        future = pd.DataFrame({"ds": pd.DatetimeIndex(dates)})
        fcst = self.model.predict(future)
        cols = ["ds", "trend"] + [
            c for c in ("weekly", "yearly") if c in fcst.columns
        ]
        return fcst[cols].rename(columns={"ds": "date"})

    # ------------------------------------------------------------------ #
    def save(self, directory: str | Path) -> None:
        from prophet.serialize import model_to_json

        if self.model is None:
            raise RuntimeError("Nothing to save: model not fitted")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / _MODEL_FILE).write_text(
            model_to_json(self.model), encoding="utf-8"
        )
        (directory / _META_FILE).write_text(
            json.dumps(
                {
                    "seasonalities": self.seasonalities_,
                    "interval_width": self.interval_width,
                    "yearly_min_days": self.yearly_min_days,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str | Path) -> "ProphetForecaster":
        from prophet.serialize import model_from_json

        directory = Path(directory)
        meta = json.loads((directory / _META_FILE).read_text(encoding="utf-8"))
        obj = cls(
            interval_width=meta.get("interval_width", 0.95),
            yearly_min_days=meta.get("yearly_min_days", 730),
        )
        obj.model = model_from_json(
            (directory / _MODEL_FILE).read_text(encoding="utf-8")
        )
        obj.seasonalities_ = meta.get("seasonalities", {})
        return obj
