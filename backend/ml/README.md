# ResiliChain AI — ML Module

Demand-forecasting and intelligence layer: **Prophet + XGBoost** trained per
product series with honest time-series evaluation, **SHAP** explainability,
a versioned model registry and a clean prediction API consumed by the
FastAPI backend. Replaces the mock forecast engine — the API contract is
unchanged.

```
Historical data → Validation → Cleaning → EDA → Feature engineering
   → Prophet + XGBoost → Time-series evaluation → Best-model selection
   → Registry (versioned) → Demand forecast + intervals → SHAP → FastAPI
```

## 1. What it does

- Loads historical sales (SQLite dev DB or CSV), validates and cleans them.
- Trains **Prophet** and **XGBoost** per product series, compares both on the
  same chronological hold-out window, and registers the winner per series —
  the data decides (in the current dev DB, Prophet wins ~6/10 series and
  XGBoost ~4/10).
- Serves forecasts with prediction intervals through
  `ml.pipeline.prediction.predict_demand`, which
  `POST /api/v1/forecast/predict` calls via
  `app/services/ml/adapter.py`. Untrained products transparently fall back
  to the original mock engine (`metrics.engine` says which one answered).
- Explains XGBoost with SHAP and Prophet with its native decomposition.

## 2. Dataset format

Canonical demand frame (what every loader produces):

| column | type | notes |
|---|---|---|
| `date` | datetime, daily | gaps are filled with 0 (dropped zero-sale days) |
| `product_id` | str | dashed UUID (or any stable id from CSV) |
| `warehouse_id` | str \| null | optional |
| `demand` | float | units sold that day |

Sources (configured in `ml/config.yaml → data.source`):

- **sqlite** (default): reads `dev.db` — `sales_history` joined to
  `retail_stores` for the warehouse link, aggregated to daily sums.
- **csv**: needs `date`, `product_id` and a demand column
  (`demand`/`quantity_sold`/`sales`); `warehouse_id`, `price`, `promotion`
  etc. optional. Drop in a real dataset without code changes.

> The dev DB now contains the **real UCI Online Retail dataset** (541k UK
> e-commerce transactions → 300 products, ~80k daily rows; imported by
> `scripts/import_sales.py`, dates re-anchored forward by whole weeks).
> It is single-warehouse, so forecasting runs at **product level**.
> Real daily SKU demand is intermittent — expect honest WAPE of ~60–110%,
> far harder than the earlier synthetic data (~7–12%).
> `ml/data/synthetic.py` remains as a clearly labelled generator for tests.

Minimum history: 90 days per series (`data.min_history_days`). With only one
observed yearly cycle, **yearly seasonality stays off** (needs
`yearly_min_days: 730`).

## 3. Installation

Everything is in `backend/requirements.txt`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. Training

```powershell
python -m ml.train                       # top 10 products (by demand), both models
python -m ml.train --model prophet       # one model only
python -m ml.train --model xgboost
python -m ml.train --product SKU-1000    # by SKU or UUID
python -m ml.train --product all --max-series 20
python -m ml.train --warehouse <uuid>    # product x warehouse series
python -m ml.train --json                # machine-readable batch report
```

What happens per series: chronological split (last 28 days = validation) →
both models fit on train only → evaluated on validation → winner selected by
**WAPE** (tie-break MAE) → both models refit on train+validation and saved as
a new version → experiment logged → SHAP/components artifacts written.

## 5. Evaluation

```powershell
python -m ml.evaluate                # per-series table: best model + metrics
python -m ml.evaluate --experiments  # full training log (every run)
python -m ml.evaluate --summary      # per-model-type aggregates (JSON)
```

Metrics: MAE, RMSE, **safe MAPE** (zero-demand points excluded; `null` if
none remain — never fabricated), sMAPE, WAPE, R² (only when actuals vary).
Splits are strictly chronological — no random train/test splitting, and all
lag/rolling features use only past values (leakage-tested in
`tests/ml/test_features.py`).

## 6. Prediction

```powershell
python -m ml.predict --product SKU-1000 --days 30
python -m ml.predict --product <uuid> --warehouse <uuid> --days 14
python -m ml.predict --product SKU-1000 --start 2026-09-01 --end 2026-09-30
python -m ml.predict --product SKU-1000 --model prophet
```

Example output (shortened):

```json
{
  "product_id": "c57cd546-04d7-4a6e-9b4a-5fd901a30243",
  "warehouse_id": null,
  "series_level": "product",
  "model": "XGBoost",
  "model_version": 1,
  "confidence_level": 0.95,
  "metrics": {"mae": 27.57, "rmse": 35.14, "mape": 9.92, "wape": 9.31},
  "metrics_source": "held-out validation window (chronological)",
  "forecast": [
    {"date": "2026-08-06", "predicted_demand": 283.9,
     "lower_bound": 222.5, "upper_bound": 342.5}
  ]
}
```

Never retrains per request: models load from the registry (cached);
intervals are Prophet's native bounds or, for XGBoost, empirical validation
residual quantiles (documented approximation). `warehouse_id` is `null`
whenever a product-level model served the request — warehouse signal is
never fabricated.

## 7. Model selection

`ml/modeling/selection.py`: lowest validation **WAPE** wins (robust with
zero-demand days), MAE breaks ties, failures are excluded. The choice and
its reason are stored in each series' `best.json`. A specific model can
always be requested explicitly (CLI `--model` / API `model` field).

## 8. SHAP

- **XGBoost** → `shap.TreeExplainer`: `feature_importance.json` (mean |SHAP|,
  signed means, top positive/negative drivers) + `shap_summary.png`
  beeswarm, per series under `ml/artifacts/shap/<series_key>/`.
- **Prophet** → SHAP does not apply; its native trend/weekly decomposition is
  exported instead (`prophet_components.json/.png`).

## 9. Artifacts

```
ml/artifacts/
├── eda/            01..06 figures + eda_report.json + validation_report.json
├── evaluation/     experiments.jsonl + experiments.csv
└── shap/<series>/  feature_importance.json, shap_summary.png,
                    prophet_components.json/.png
ml/models/
└── <series_key>/   prophet/vN/, xgboost/vN/ (+metadata.json), best.json
```

Both directories are gitignored (binary/generated).

## 10. Backend integration

```
Frontend → POST /api/v1/forecast/predict → ForecastService
  → app/services/ml/adapter.py (MLForecastEngine)
      → ml.pipeline.prediction.predict_demand → registry → saved model
  → (no trained model? → original mock engine, marked "engine": "mock")
```

- API contract untouched (`ForecastPredictRequest/Response`); real runs add
  provenance to `metrics`: `engine`, `model_version`, `series_level`,
  `metrics_source`, `dataset_version`.
- `GET /forecast/models` flips prophet/xgboost to `status: "available"` with
  **real averaged validation metrics** once models exist; LSTM remains
  `planned` (intentionally not implemented).
- ML calls run in a worker thread (`anyio.to_thread`) — the event loop is
  never blocked. If ML dependencies are missing entirely, the backend still
  boots and serves mock forecasts.
- Digital-twin / Monte-Carlo / recommendations integrate by consuming
  `predict_demand` output — forecasting stays free of their logic.

## 11. Common errors

| Error | Cause / fix |
|---|---|
| `ModelNotTrainedError: No trained model for product …` | Run `python -m ml.train --product <id>` (API falls back to mock automatically) |
| `InsufficientHistoryError` | Series shorter than `min_history_days` (90) or the 28-day feature warm-up |
| `DataValidationError: SQLite database not found` | Run from `backend/` or fix `data.sqlite_path` |
| `CSV must contain a demand column` | Rename your column to `demand`/`quantity_sold`/`sales` |
| `ModuleNotFoundError: prophet` | venv not active / `pip install -r requirements.txt` |
| Metrics show `mape: null` | All validation actuals were zero — MAPE undefined; use sMAPE/WAPE |
| Prophet interval bounds differ between calls | Expected: Prophet samples its uncertainty intervals; `yhat` is deterministic |

## Tests

```powershell
python -m pytest tests/ml -q      # 49 ML tests (validation, features/leakage,
                                  # models, metrics, pipeline, SHAP)
python -m pytest -q               # full backend suite
```
