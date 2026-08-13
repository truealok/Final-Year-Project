# ResiliChain AI — Project Summary

> **Final Year Engineering Project** — Intelligent Supply Chain Forecasting &
> Resilience Simulator

Last updated: 2026-08-12

---

## 1. What is this project? (in easy words)

Imagine a company that makes products, stores them in warehouses, and sells
them through retail stores. Every day they face questions like:

- *"How many units of this product will we sell next month?"*
- *"If our supplier fails or a flood hits a warehouse, how badly are we hurt?"*
- *"Which products are about to run out of stock?"*
- *"What should we do about it?"*

**ResiliChain AI answers these questions.** It is a web platform where a
supply-chain team can:

1. **See everything at a glance** — a dashboard with sales, inventory,
   alerts and risk scores.
2. **Predict future demand** — real machine-learning models (Prophet and
   XGBoost) learn from past sales and forecast what will sell next, with
   confidence ranges and an explanation of *why* the model thinks so (SHAP).
3. **Simulate disasters** — "what if a supplier fails for 2 weeks?" and see
   the estimated impact before it happens.
4. **View the supply network as a living map** (digital twin) — factories →
   warehouses → stores, with health and risk per node.
5. **Get recommendations** — e.g. "increase safety stock for product X".
6. **Export reports** — CSV / PDF summaries for management.

It has login with roles (Admin, Manager, Analyst), so different people see
and can do different things.

---

## 2. Tech stack

| Layer | Technology | Used for |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite | The dashboard web app |
| | Tailwind CSS + shadcn-style components | Styling / UI kit |
| | TanStack React Query | Server data fetching & caching |
| | Recharts + React Flow | Charts + the digital-twin network map |
| **Backend** | Python (3.11+) + FastAPI (async) | REST API |
| | SQLAlchemy 2.0 (async) + Alembic | Database ORM + migrations |
| | Pydantic v2 | Request/response validation |
| | JWT (access + rotating refresh) + bcrypt | Authentication & security |
| | SQLite (dev) / PostgreSQL (prod-ready) | Database |
| **Machine Learning** | Prophet | Time-series forecasting (trend + seasonality) |
| | XGBoost | Gradient-boosted trees over lag/rolling features |
| | SHAP | Explaining *why* the model predicts what it predicts |
| | pandas + NumPy + scikit-learn | Data processing & metrics |
| | Matplotlib | EDA and explainability figures |
| **Testing** | Pytest (83 tests) | Backend + ML test suites |

---

## 3. Project tree

```
alok/
├── README.md                     # main guide: setup + start commands
├── PROJECT_SUMMARY.md            # this file
│
├── backend/                      # FastAPI REST API (Python)
│   ├── app/
│   │   ├── main.py               # app factory, middleware, startup
│   │   ├── core/                 # config, database, JWT security, DI
│   │   ├── api/v1/               # 13 routers: auth, users, dashboard,
│   │   │                         #   forecast, simulation, digital-twin,
│   │   │                         #   inventory, suppliers, warehouses,
│   │   │                         #   analytics, recommendations, reports, alerts
│   │   ├── models/               # 16 SQLAlchemy models (products, sales, ...)
│   │   ├── schemas/              # Pydantic request/response contracts
│   │   ├── repositories/         # all database access
│   │   ├── services/             # business logic
│   │   │   └── ml/               # adapter: FastAPI ↔ ML module bridge
│   │   ├── middleware/           # logging, timing, rate limit, errors
│   │   └── utils/                # exceptions, pagination, logger
│   │
│   ├── ml/                       # ★ MACHINE LEARNING MODULE ★
│   │   ├── config.yaml           # every ML knob in one file
│   │   ├── data/                 # loaders (SQLite/CSV), validation,
│   │   │                         #   cleaning, synthetic generator
│   │   ├── eda/                  # exploratory analysis (6 figures + report)
│   │   ├── features/             # leakage-safe lag/rolling features
│   │   ├── modeling/             # Prophet, XGBoost, metrics, selection,
│   │   │                         #   versioned model registry
│   │   ├── explain/              # SHAP (XGBoost) + Prophet components
│   │   ├── pipeline/             # train & predict orchestration
│   │   ├── train.py / evaluate.py / predict.py   # CLI commands
│   │   ├── models/               # saved trained models (gitignored)
│   │   ├── artifacts/            # figures, experiment logs (gitignored)
│   │   ├── docs/AUDIT.md         # repository + dataset audit report
│   │   └── README.md             # full ML documentation
│   │
│   ├── alembic/                  # DB migrations
│   ├── scripts/seed.py           # demo-data generator (50 products,
│   │                             #   365 days of sales, users, alerts...)
│   ├── tests/                    # 34 API tests + 49 ML tests
│   ├── dev.db                    # SQLite dev database (seeded)
│   ├── .env                      # local config (SQLite by default)
│   └── requirements.txt
│
└── frontend/                     # React dashboard (TypeScript)
    ├── src/
    │   ├── pages/                # dashboard, forecast, simulation,
    │   │                         #   digital-twin, inventory, suppliers,
    │   │                         #   warehouses, analytics, alerts,
    │   │                         #   recommendations, reports, settings, auth
    │   ├── components/           # ui primitives, KPI cards, charts
    │   ├── features/             # digital-twin nodes/panels
    │   ├── layouts/              # sidebar + topbar app shell
    │   ├── hooks/                # auth, theme, React Query hooks
    │   ├── services/             # typed API client
    │   ├── types/                # TS types mirroring backend schemas
    │   └── utils/
    ├── package.json
    └── vite.config.ts
```

---

## 4. What is DONE ✅

### Platform (was already built)
- ✅ Full FastAPI backend — Clean Architecture (routes → services →
  repositories → models), global error handling, request logging/timing
- ✅ JWT auth with roles (Admin / Manager / Analyst), signup/login/refresh/
  password reset
- ✅ All 13 API modules: dashboard, forecast, simulation, digital twin,
  inventory, suppliers, warehouses, analytics, recommendations, reports
  (CSV/PDF export), alerts, users
- ✅ Complete React dashboard — every page implemented, dark mode, role-aware
  UI, charts, digital-twin network view
- ✅ Seed script: realistic demo data (50 products, 20 suppliers,
  10 warehouses, 15 stores, 365 days of sales, ~18k rows)
- ✅ SQLite dev setup (zero-config) with PostgreSQL-ready config

### Real data (replaced the synthetic demo data) ★
- ✅ **Real public dataset imported**: UCI Online Retail (CC BY 4.0) —
  541,909 genuine UK e-commerce transactions → cleaned to **300 real
  products and ~80k daily sales rows** across 11 country-level stores
  (`scripts/import_sales.py`, works with any CSV too)
- ✅ Dates re-anchored forward by whole weeks so the data ends this week —
  demand values and weekday patterns are untouched real data
  (`--no-shift` keeps the original 2010–11 dates)
- ✅ Seeded demo logins removed — **the first account you sign up becomes
  admin**
- ✅ ML retrained on the real data (EDA shows the real patterns: Thursday
  peak, Saturday trough — this store barely ships weekends)

### Machine Learning layer (built in this phase) ★
- ✅ **Repository & dataset audit** (`ml/docs/AUDIT.md`) — before any code
- ✅ **Data pipeline**: SQLite/CSV loaders → validation report → cleaning
  (duplicates summed, gaps filled, outliers flagged) — plus a clearly
  labelled synthetic-data generator for tests
- ✅ **EDA**: 6 figures + conclusions computed from the data (trend,
  weekly seasonality, top products, distribution)
- ✅ **Feature engineering**: calendar + lag (1/7/14/28) + rolling
  mean/std features, **leakage-proof** (windows end at t-1; unit-tested)
- ✅ **Prophet model** — weekly seasonality on, yearly correctly OFF
  (only 1 year of history), native confidence intervals
- ✅ **XGBoost model** — recursive multi-day forecasting, early stopping,
  empirical residual intervals
- ✅ **Honest evaluation** — chronological splits only (never random),
  MAE / RMSE / safe-MAPE / sMAPE / WAPE, all from real runs
- ✅ **Best-model selection per product** — the data decides: currently
  Prophet wins 6 series, XGBoost 4 (validation WAPE ≈ 7–12%)
- ✅ **Versioned model registry** + experiment log (every training run
  recorded with metrics and duration)
- ✅ **SHAP explainability** — real feature importance (lag_7 is the top
  driver), summary plots; Prophet explained via its own decomposition
- ✅ **Prediction API** — `predict_demand()`: loads saved model, never
  retrains per request, returns forecast + bounds + real metrics
- ✅ **CLI tools** — `python -m ml.train / evaluate / predict / eda`
- ✅ **FastAPI integration** — `POST /forecast/predict` now serves real
  ML forecasts for trained products and transparently falls back to the
  mock engine for untrained ones (`metrics.engine` = `"ml"` or `"mock"`);
  `GET /forecast/models` shows real averaged metrics. **API contract
  unchanged — the frontend needed zero changes.**
- ✅ **Tests: 83/83 passing** (49 new ML tests incl. leakage prevention)
- ✅ 10 products trained end-to-end and verified live through the API

---

## 5. What is PENDING ⏳

| Item | Notes |
|---|---|
| ⏳ **NetworkX digital twin** | The network view currently uses deterministic mock data. Plan: build a real graph model that consumes ML forecasts (`predict_demand`) to compute node risk/impact. The interface is already defined. |
| ⏳ **Monte Carlo simulation** | `POST /simulation/run` is still a mock engine. Plan: real Monte Carlo runs over forecasted demand + inventory + lead times + disruption parameters. |
| ⏳ **Smarter recommendations** | Currently generated from templates. Plan: rule-based engine combining forecast ↑ + inventory ↓ + supplier risk ↑ → concrete actions. |
| ⏳ **LSTM model** | Intentionally not implemented (per project decision). The API already reserves the `lstm` option; requests fall back to mock. |
| ⏳ **Train remaining products** | 10/300 real products have trained models (config cap `batch.max_series`). Run `python -m ml.train --product all --max-series 300` to cover more. |
| ⏳ **Forecast accuracy on real data** | Real daily single-product e-commerce demand is intermittent — validation WAPE is ~60–110% (honest numbers, typical for this dataset at daily SKU level). Improving it (weekly aggregation, intermittent-demand models like Croston, price/promo features) is a good next research step. |
| ⏳ **Warehouse-level forecasting** | The real dataset is single-warehouse e-commerce, so only product-level series exist. Works automatically once multi-warehouse sales data is loaded. |
| ⏳ **Suppliers / inventory data** | The public dataset has no supplier or stock-level info — those pages start empty and are filled manually via the UI (admin/manager). |
| ⏳ **Scheduled retraining** | Models are trained manually via CLI. Plan: periodic retrain job (cron / background task) + drift monitoring. |
| ⏳ **Production deployment** | PostgreSQL migration (Alembic ready), Docker images, CI pipeline — configs exist, deployment not set up. |

---

## 6. How to run (quick reference)

```powershell
# Backend (terminal 1)
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload        # → http://localhost:8000/docs

# Frontend (terminal 2)
cd frontend
npm run dev                          # → http://localhost:5173

# Data (from backend/, venv active) — real dataset already imported;
# to redo it:
python -m scripts.import_sales "data/Online Retail.xlsx" --reset

# ML
python -m ml.eda                     # analyze the data
python -m ml.train                   # train models (top 10 products)
python -m ml.evaluate                # compare model metrics
python -m ml.predict --product 22197 --days 30   # a real product SKU

# Login: sign up in the app — the FIRST account becomes admin
```

More detail: [README.md](README.md) · [backend/README.md](backend/README.md) ·
[backend/ml/README.md](backend/ml/README.md) · [frontend/README.md](frontend/README.md)
