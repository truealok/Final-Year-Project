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
| Database | PostgreSQL (SQLite in-memory for tests) |
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

### ML placeholders (by design)

Prophet, XGBoost, LSTM, SHAP, NetworkX and Monte Carlo are **intentionally
not implemented**. `ForecastService`, `SimulationService` and
`DigitalTwinService` produce realistic, deterministic mock output behind the
final API contracts — swap the private generation methods for real engines
later **without changing any route or schema**.

## Quick start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (source .venv/bin/activate on Unix)
pip install -r requirements.txt

copy .env.example .env          # then edit DATABASE_URL / JWT_SECRET_KEY
```

Start PostgreSQL (example with Docker):

```bash
docker run -d --name resilichain-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=resilichain postgres:16
```

Seed enterprise mock data (50 products, 20 suppliers, 5 factories,
10 warehouses, 15 retail stores, 365 days of sales, forecasts, simulations,
alerts, recommendations):

```bash
python -m scripts.seed            # or: python -m scripts.seed --reset
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs**.

### Seeded logins

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
