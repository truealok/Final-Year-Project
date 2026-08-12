# ResiliChain AI

**Intelligent Supply Chain Forecasting & Resilience Simulator**

Full-stack platform: a FastAPI backend (Clean Architecture, JWT auth, mock ML
engines behind final API contracts) and a React dashboard (Vite + TypeScript +
Tailwind).

## Project structure

```
alok/
├── backend/                      # FastAPI REST API (Python)
│   ├── app/
│   │   ├── main.py               # app factory, middleware, lifespan
│   │   ├── core/                 # config, database, security, DI
│   │   ├── api/v1/               # 13 routers (controllers)
│   │   ├── models/               # SQLAlchemy 2.0 models + enums
│   │   ├── schemas/              # Pydantic v2 request/response models
│   │   ├── repositories/         # data access layer
│   │   ├── services/             # business logic + mock ML engines
│   │   ├── middleware/           # logging, timing, rate limit, errors
│   │   └── utils/                # exceptions, pagination, logger
│   ├── alembic/                  # async DB migrations
│   ├── scripts/seed.py           # enterprise mock data generator
│   ├── tests/                    # pytest suite (in-memory SQLite)
│   ├── .venv/                    # Python virtual environment (local)
│   ├── .env                      # local config (copy of .env.example)
│   ├── dev.db                    # SQLite dev database
│   └── requirements.txt
│
└── frontend/                     # React dashboard (TypeScript)
    ├── src/
    │   ├── components/           # ui primitives, common widgets, charts
    │   ├── features/             # feature composites (digital twin, …)
    │   ├── layouts/              # app shell: sidebar, topbar
    │   ├── pages/                # one file per route
    │   ├── hooks/                # auth, theme, React Query hooks
    │   ├── services/             # typed API client
    │   ├── types/                # API types mirroring backend schemas
    │   └── utils/                # formatting, constants, helpers
    ├── package.json
    └── vite.config.ts
```

## Quick start

### 1. Backend (http://localhost:8000)

```powershell
cd backend

# First time only: create venv + install deps + create .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# For local dev without PostgreSQL, set in .env:
#   DATABASE_URL=sqlite+aiosqlite:///./dev.db

# Load data (pick ONE):
python -m scripts.import_sales "data/Online Retail.xlsx" --reset
#   ^ REAL dataset (UCI Online Retail — 300 products, ~80k daily sales rows)
python -m scripts.seed_network --reset
#   ^ then add the configured supply-chain network (suppliers/factories/
#     warehouses/routes/inventory sized from the real demand)
# python -m scripts.seed
#   ^ or synthetic demo data (fake products/suppliers/logins)

# Start the API
uvicorn app.main:app --reload
```

> ⚠️ **Always activate the venv first** (`.\.venv\Scripts\Activate.ps1`).
> Running the globally-installed `uvicorn` uses the wrong Python and fails
> with `ModuleNotFoundError: No module named 'sqlalchemy'`.
> Alternative that always works without activating:
> `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 2. Frontend (http://localhost:5173)

In a **second terminal** (backend must already be running — the dev server
proxies `/api` to port 8000):

```powershell
cd frontend
npm install          # first time only
npm run dev
```

### 3. Sign in

**The first account you sign up becomes admin** — open the app and register.
Later signups start as analyst and can be promoted by the admin.

(Only if you loaded the synthetic demo data with `python -m scripts.seed`,
these accounts exist instead: `admin@resilichain.ai` / `Admin@123`,
`manager@…` / `Manager@123`, `analyst@…` / `Analyst@123`.)

## Common commands

| Task | Directory | Command |
|---|---|---|
| Start API (dev, hot-reload) | `backend/` | `uvicorn app.main:app --reload` |
| Import REAL dataset | `backend/` | `python -m scripts.import_sales "data/Online Retail.xlsx" --reset` |
| Create configured network | `backend/` | `python -m scripts.seed_network --reset` |
| Seed synthetic demo data | `backend/` | `python -m scripts.seed --reset` |
| Train ML models | `backend/` | `python -m ml.train` |
| Backend tests | `backend/` | `pytest -q` |
| DB migrations | `backend/` | `alembic upgrade head` |
| Start dashboard (dev) | `frontend/` | `npm run dev` |
| Production build | `frontend/` | `npm run build` |

## Database options

- **SQLite (default for dev)** — zero setup: `DATABASE_URL=sqlite+aiosqlite:///./dev.db`
  in `backend/.env`. Tables are auto-created on startup (`AUTO_CREATE_TABLES=true`).
- **PostgreSQL** — set `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/resilichain`
  and start Postgres, e.g. with Docker:

  ```bash
  docker run -d --name resilichain-db -p 5432:5432 \
    -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=resilichain postgres:16
  ```

See [backend/README.md](backend/README.md) for architecture, API reference and
roles; [frontend/README.md](frontend/README.md) for the dashboard stack and
structure.
