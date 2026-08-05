# ResiliChain AI — Frontend

Enterprise React dashboard for the ResiliChain AI supply chain platform.

## Stack

React 18 · TypeScript · Vite · Tailwind CSS · shadcn/ui-style components ·
React Router · TanStack React Query · Recharts · React Flow (@xyflow/react) ·
Framer Motion · Lucide icons · Sonner toasts.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The dev server proxies `/api` to the backend at `http://localhost:8000`, so
start the backend first (from `backend/`):

```bash
uvicorn app.main:app --reload
```

Sign in with a seeded account (see backend README):
`admin@resilichain.ai / Admin@123`.

For production builds set `VITE_API_URL` (see `.env.example`) and run
`npm run build` — output lands in `dist/`.

## Structure

```
src/
├── components/
│   ├── ui/          # shadcn-style primitives (button, dialog, table, …)
│   ├── common/      # KPI card, chart card, page header, badges, skeletons…
│   └── charts/      # dataviz-compliant Recharts wrappers + risk heatmap
├── features/        # feature-specific composites (digital twin nodes/panel)
├── layouts/         # app shell: sidebar, topbar, search, notifications
├── pages/           # one file per route — no placeholders
├── hooks/           # auth, theme, media query, React Query hooks
├── services/        # typed API client + endpoint groups
├── types/           # API types mirroring backend schemas
└── utils/           # formatting, constants, downloads, derived fields
```

## Notes

- **Auth**: JWT access + rotating refresh tokens; the client refreshes
  transparently on 401 and redirects to login when the session dies.
- **Roles**: create/edit/delete actions are shown only to admin and
  supply-chain-manager roles (the backend enforces them regardless).
- **Dark mode**: class-based, persisted, `system` aware — toggle in the topbar.
- **Charts**: categorical palette is CVD-validated for both themes; single-hue
  sequential ramp for the risk heatmap; legends whenever ≥ 2 series.
- **Derived display fields** (reserved/incoming stock, node health, lead time
  for non-supplier nodes) are deterministic client-side stand-ins until the
  backend tracks them — stable per entity across sessions.
