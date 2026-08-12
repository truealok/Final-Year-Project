# ResiliChain AI — Backend

**Intelligent Supply Chain Forecasting & Resilience Simulator**

Production-ready FastAPI backend built with Clean Architecture. Every endpoint
returns realistic data (from the database and deterministic mock engines) so a
frontend is fully functional **before** the ML models are integrated.

## Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI (async) |
| Server | Uvicorn |
| Database | PostgreSQL or SQLite for dev (SQLite in-memory for tests) |
| ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic v2 |
| Auth | JWT (access + rotating refresh tokens), bcrypt |
| Migrations | Alembic (async template) |
| Docs | Swagger UI at `/docs`, ReDoc at `/redoc` |
| Testing | Pytest + pytest-asyncio + httpx |

## Architecture

```
Controller (app/api/v1)        thin routes, no business logic
        ↓
Service    (app/services)      business logic, mock ML engines
        ↓
Repository (app/repositories)  all database access
        ↓
Database   (app/models)        SQLAlchemy 2.0 models, UUID PKs, timestamps
```

- **Dependency injection** end to end: routes receive services, services
  receive repositories, repositories receive the request-scoped session
  (`app/core/dependencies.py`).
- **Global exception handling**: every error becomes
  `{"error": {"code", "message", "details"}}` with the right status
  (400/401/403/404/409/422/429/500).
- **Middleware**: CORS, auth context, request logging, request timing
  (`X-Process-Time-Ms`), rate limiting (ready — off by default).

### Intelligence layer (implemented)

**ML — Prophet, XGBoost, SHAP** ([`ml/`](ml/README.md)): per-product
training with chronological validation, best-model selection, a versioned
registry and real metrics. `POST /forecast/predict` serves trained models
through `app/services/ml/adapter.py` and falls back to the deterministic
mock for untrained products (`metrics.engine` tells you which). Train with
`python -m ml.train`.

**Digital twin — NetworkX** (`app/services/twin_graph.py`): a real directed
graph (suppliers → factories → warehouses → stores) built from the database.
Node risk is **computed**: warehouse risk from inventory cover days vs real
demand, factory risk from utilization vs downstream demand, supplier risk
from reliability. Network resilience is a documented composite (30%
redundancy + 30% inventory coverage + 25% supplier reliability + 15% store
connectivity).

**Disruption simulation — Monte Carlo** (`app/services/simulation_engine.py`):
day-by-day inventory/service simulation over the same graph. Per replication
demand is sampled from real per-store statistics, disruptions propagate
supplier → factory → warehouse, and

```
resilience = area under disrupted service curve / area under baseline curve
```

(paired demand draws, mean over N configurable replications). Expected cost
uses the real average unit price; stockout probability, recovery time
(service AND inventory position restored), service level and CO₂ (configured
per-mode emission factors) all emerge from the simulation. Six scenario
types: supplier failure, transport delay, flood, demand spike, warehouse
failure, machine breakdown.

**Recommendations** (`app/services/recommendation_service.py`): transparent
rule engine over real signals — sales growth × inventory cover, positions
below reorder point, supplier reliability gaps, warehouse imbalance and
low-resilience simulation follow-ups. Every number in a recommendation is
computed and stored in its `context`.

**Dashboard**: every KPI computed — forecast accuracy = 100 − mean
validation WAPE from the ML registry; resilience/cost/stockout/recovery from
recent simulations (or derived from the network snapshot); carbon from
configured emission factors × real demand flows.

**Data provenance:** product demand is the real UCI dataset; network
entities and parameters (suppliers, factories, warehouses, routes,
capacities, lead times, emission factors) are **configured** values created
by `python -m scripts.seed_network` — never presented as observed data.
LSTM remains intentionally not implemented.

## Quick start

### 1. Setup (first time only)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell  (source .venv/bin/activate on Unix)
pip install -r requirements.txt

copy .env.example .env          # then edit DATABASE_URL / JWT_SECRET_KEY
```

### 2. Choose a database

**Option A — SQLite (zero setup, recommended for dev).** In `.env` set:

```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
```

Tables are auto-created on startup (`AUTO_CREATE_TABLES=true`).

**Option B — PostgreSQL.** Keep the default `DATABASE_URL` from
`.env.example` and start Postgres (example with Docker):

```bash
docker run -d --name resilichain-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=resilichain postgres:16
```

### 3. Load data

**Option A — REAL dataset (recommended).** UCI Online Retail (CC BY 4.0):
541k genuine UK e-commerce transactions → 300 products, ~80k daily sales
rows, stores per country. Dates are re-anchored forward by whole weeks so
the data ends this week (values/weekday patterns untouched; `--no-shift`
keeps 2010-11 dates):

```bash
# one-time download: https://archive.ics.uci.edu/static/public/352/online+retail.zip
#   → unzip into data/
python -m scripts.import_sales "data/Online Retail.xlsx" --reset
```

Works with any CSV that has `date, product/StockCode, quantity, price`
columns. No seeded logins — **the first signup becomes admin**.

**Option B — synthetic demo data.** 50 fake products, suppliers,
warehouses, 365 days of generated sales + demo logins:

```bash
python -m scripts.seed            # or: python -m scripts.seed --reset
```

### 4. Run the API

```powershell
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs**.

> ⚠️ **The venv must be active** when you run `uvicorn`. If you see
> `ModuleNotFoundError: No module named 'sqlalchemy'`, you're using a
> globally-installed uvicorn with the wrong Python. Either activate the venv
> first (`.\.venv\Scripts\Activate.ps1`) or run it explicitly:
>
> ```powershell
> .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
> ```

### Logins

With the real dataset there are **no pre-made accounts** — sign up and the
first account becomes admin. Only the synthetic seed (`scripts.seed`)
creates demo logins:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@resilichain.ai` | `Admin@123` |
| Supply Chain Manager | `manager@resilichain.ai` | `Manager@123` |
| Analyst | `analyst@resilichain.ai` | `Analyst@123` |

> Signing up via the API: the **first** account ever created becomes admin;
> all later signups start as analyst and can be promoted via `PATCH
> /api/v1/users/{id}`.

## Migrations

`AUTO_CREATE_TABLES=true` creates tables on startup for development. For
production use Alembic:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## Tests

```bash
pytest -q
```

The suite runs against in-memory SQLite — no PostgreSQL needed.

## API overview (prefix `/api/v1`)

| Module | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `/auth/login`, `/auth/token` (Swagger form), `/auth/refresh`, `/auth/logout`, `/auth/forgot-password`, `/auth/reset-password`, `GET /auth/me` |
| Users | `GET /users`, `GET/PATCH/DELETE /users/{id}`, `PATCH /users/me` (admin-gated) |
| Dashboard | `GET /dashboard` — accuracy, resilience, cost, inventory, stockout, recovery, carbon, alerts, simulations |
| Forecast | `POST /forecast/predict`, `GET /forecast/history`, `GET /forecast/models` |
| Simulation | `POST /simulation/run`, `GET /simulation/history`, `GET /simulation/types` |
| Digital Twin | `GET /digital-twin/network` — nodes, edges, summary |
| Inventory | CRUD `/inventory`, `GET /inventory/summary`, `/inventory/products`, `/inventory/categories` |
| Suppliers | CRUD `/suppliers` (+ country/risk/status/search filters) |
| Warehouses | CRUD `/warehouses` (responses include utilization) |
| Analytics | `GET /analytics` — demand, inventory, supplier, warehouse, disruption, recovery, carbon series |
| Recommendations | `GET /recommendations`, `POST /recommendations/generate`, `PATCH /recommendations/{id}` |
| Reports | `POST /reports/generate`, `GET /reports`, `GET /reports/{id}`, `GET /reports/{id}/export?export_format=csv|pdf`, `DELETE /reports/{id}` |
| Alerts | `GET /alerts`, `GET /alerts/summary`, `POST /alerts`, `PATCH /alerts/{id}/read`, `PATCH /alerts/read-all`, `DELETE /alerts/{id}` |

### Roles & authorization

| Action | Admin | Manager | Analyst |
|---|---|---|---|
| Read data / run forecasts & simulations | ✅ | ✅ | ✅ |
| Create/update/delete suppliers, warehouses, inventory, alerts, reports | ✅ | ✅ | ❌ |
| Manage users | ✅ | ❌ | ❌ |

## Project structure

```
backend/
├── app/
│   ├── main.py               # app factory, middleware, lifespan
│   ├── core/                 # config, database, security, DI
│   ├── api/v1/               # 13 routers (controllers)
│   ├── models/               # 16 SQLAlchemy models + enums
│   ├── schemas/              # Pydantic v2 request/response models
│   ├── repositories/         # data access (generic base + per-aggregate)
│   ├── services/             # business logic + mock ML engines
│   ├── middleware/           # logging, timing, rate limit, auth ctx, errors
│   └── utils/                # exceptions, pagination, logger
├── alembic/                  # async migration environment
├── scripts/seed.py           # enterprise mock data generator
├── tests/                    # pytest suite (SQLite in-memory)
├── requirements.txt
└── .env.example
```
