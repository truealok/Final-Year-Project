"""XGBoost forecaster.

Gradient-boosted trees over the leakage-safe features from
:mod:`ml.features.engineering`. Multi-day forecasts are produced
**recursively**: each predicted day is appended to the history so the next
day's lags/rollings can be computed — exactly the information that would be
available in production.

Prediction intervals
--------------------
XGBoost gives point predictions only. Intervals here are **empirical residual
intervals**: the (1±confidence)/2 quantiles of the *validation* residuals
(actual − predicted) are stored at fit time and added to each prediction.
This is an honest, documented approximation — it assumes future errors look
like validation errors and does not widen with horizon.

Persistence: the booster is saved with XGBoost's native JSON format (safe,
version-tolerant); wrapper state (feature columns, residual quantiles,
params) goes to a sidecar JSON. No pickling of arbitrary objects.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.exceptions import InsufficientHistoryError
from ml.features.engineering import features_for_date, make_supervised

MODEL_TYPE = "xgboost"
_MODEL_FILE = "model.ubj"
_META_FILE = "xgb_meta.json"


class XGBForecaster:
    def __init__(
        self,
        lags: list[int] | None = None,
        rolling_windows: list[int] | None = None,
        rolling_std_windows: list[int] | None = None,
        n_estimators: int = 400,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        subsample: float = 0.9,
        colsample_bytree: float = 0.9,
        min_child_weight: float = 3.0,
        early_stopping_rounds: int = 40,
        confidence_level: float = 0.95,
        random_seed: int = 42,
    ) -> None:
        self.lags = list(lags or [1, 7, 14, 28])
        self.rolling_windows = list(rolling_windows or [7, 14, 28])
        self.rolling_std_windows = list(rolling_std_windows or [7, 28])
        self.params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "min_child_weight": min_child_weight,
        }
        self.early_stopping_rounds = early_stopping_rounds
        self.confidence_level = confidence_level
        self.random_seed = random_seed
        self.model = None
        self.feature_cols: list[str] = []
        self.residual_lower_: float = 0.0
        self.residual_upper_: float = 0.0

    # ------------------------------------------------------------------ #
    @property
    def _max_warmup(self) -> int:
        return max(
            self.lags + self.rolling_windows + self.rolling_std_windows
        )

    def fit(
        self, series: pd.DataFrame, eval_tail_days: int = 28
    ) -> "XGBForecaster":
        """Fit on one series (columns: date, demand).

        The last *eval_tail_days* of the series act as the early-stopping
        eval set and provide the residual quantiles for intervals. They are
        part of the supplied series — pass the TRAIN split only, so the
        model never sees the validation/test windows used for comparison.
        """
        import xgboost as xgb

        frame, cols = make_supervised(
            series, self.lags, self.rolling_windows, self.rolling_std_windows
        )
        self.feature_cols = cols
        if len(frame) < max(2 * eval_tail_days, 30):
            raise InsufficientHistoryError(
                f"Series has {len(frame)} usable rows after the "
                f"{self._max_warmup}-day feature warm-up; need at least "
                f"{max(2 * eval_tail_days, 30)}"
            )

        cutoff = frame["date"].max() - pd.Timedelta(days=eval_tail_days - 1)
        train_part = frame[frame["date"] < cutoff]
        eval_part = frame[frame["date"] >= cutoff]

        x_train = train_part[cols].to_numpy(dtype=float)
        y_train = train_part["demand"].to_numpy(dtype=float)
        x_eval = eval_part[cols].to_numpy(dtype=float)
        y_eval = eval_part["demand"].to_numpy(dtype=float)

        self.model = xgb.XGBRegressor(
            **self.params,
            random_state=self.random_seed,
            objective="reg:squarederror",
            early_stopping_rounds=(
                self.early_stopping_rounds if len(eval_part) else None
            ),
        )
        self.model.fit(
            x_train,
            y_train,
            eval_set=[(x_eval, y_eval)] if len(eval_part) else None,
            verbose=False,
        )

        # Residual quantiles from the eval tail → empirical intervals.
        if len(eval_part):
            residuals = y_eval - self.model.predict(x_eval)
        else:  # degenerate fallback: in-sample residuals (documented optimism)
            residuals = y_train - self.model.predict(x_train)
        alpha = (1 - self.confidence_level) / 2
        self.residual_lower_ = float(np.quantile(residuals, alpha))
        self.residual_upper_ = float(np.quantile(residuals, 1 - alpha))
        return self

    # ------------------------------------------------------------------ #
    def predict_recursive(
        self, history: pd.DataFrame, dates: pd.DatetimeIndex | list
    ) -> pd.DataFrame:
        """Forecast the given *dates* given observed *history*.

        History gaps between its last date and the first requested date are
        bridged by predicting the intermediate days too (they are then
        discarded from the returned frame).
        """
        if self.model is None:
            raise RuntimeError("XGBForecaster.predict called before fit/load")
        req = pd.DatetimeIndex(dates).sort_values()
        hist = (
            history[["date", "demand"]]
            .sort_values("date")
            .set_index("date")["demand"]
            .astype(float)
        )
        # Only information from BEFORE the requested window may be used —
        # also prevents duplicate index entries when ranges overlap history.
        hist = hist[hist.index < req[0]]
        if len(hist) < self._max_warmup:
            raise InsufficientHistoryError(
                f"Need >= {self._max_warmup} days of history before "
                f"{req[0].date()} for features; got {len(hist)}"
            )

        # Bridge any gap between the end of history and the last requested
        # day by predicting every intermediate day recursively.
        first_needed = hist.index.max() + pd.Timedelta(days=1)
        all_days = pd.date_range(first_needed, req[-1], freq="D")
        preds: dict[pd.Timestamp, float] = {}
        for day in all_days:
            row = features_for_date(
                hist,
                day,
                self.lags,
                self.rolling_windows,
                self.rolling_std_windows,
            )
            if row is None:  # cannot happen after the check above
                raise InsufficientHistoryError("history too short mid-recursion")
            x = np.array(
                [[row[c] for c in self.feature_cols]], dtype=float
            )
            yhat = max(0.0, float(self.model.predict(x)[0]))
            preds[day] = yhat
            hist = pd.concat([hist, pd.Series([yhat], index=[day])])

        out = pd.DataFrame(
            {
                "date": req,
                "yhat": [preds[d] for d in req],
            }
        )
        out["yhat_lower"] = (out["yhat"] + self.residual_lower_).clip(lower=0.0)
        out["yhat_upper"] = (out["yhat"] + self.residual_upper_).clip(lower=0.0)
        out["yhat_lower"] = out[["yhat_lower", "yhat"]].min(axis=1)
        out["yhat_upper"] = out[["yhat_upper", "yhat"]].max(axis=1)
        return out

    # ------------------------------------------------------------------ #
    def save(self, directory: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Nothing to save: model not fitted")
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.model.save_model(directory / _MODEL_FILE)
        (directory / _META_FILE).write_text(
            json.dumps(
                {
                    "lags": self.lags,
                    "rolling_windows": self.rolling_windows,
                    "rolling_std_windows": self.rolling_std_windows,
                    "feature_cols": self.feature_cols,
                    "params": self.params,
                    "confidence_level": self.confidence_level,
                    "residual_lower": self.residual_lower_,
                    "residual_upper": self.residual_upper_,
                    "random_seed": self.random_seed,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str | Path) -> "XGBForecaster":
        import xgboost as xgb

        directory = Path(directory)
        meta = json.loads((directory / _META_FILE).read_text(encoding="utf-8"))
        obj = cls(
            lags=meta["lags"],
            rolling_windows=meta["rolling_windows"],
            rolling_std_windows=meta["rolling_std_windows"],
            confidence_level=meta.get("confidence_level", 0.95),
            random_seed=meta.get("random_seed", 42),
            **meta.get("params", {}),
        )
        obj.model = xgb.XGBRegressor()
        obj.model.load_model(directory / _MODEL_FILE)
        obj.feature_cols = meta["feature_cols"]
        obj.residual_lower_ = meta.get("residual_lower", 0.0)
        obj.residual_upper_ = meta.get("residual_upper", 0.0)
        return obj
