# H2O Hackathon 2026 — Predictive Water Intelligence

Local-only MVP for the Sacramento River basin / Shasta Lake. Two services:

- `backend/` — FastAPI sidecar. Loads `data/challenge.csv`, pulls live reservoir
  storage from CDEC (sensor 15 at station SHA), computes per-month percentile
  bands, a composite risk score, threshold alerts, and a seasonal-naive forecast.
- `frontend/` — Next.js 15 dashboard. Server-renders the snapshot, trends,
  forecast strip, and alerts in one page.

## Run both

In two terminals:

```bash
# terminal 1 — backend
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

## Where to extend

- New live feeds: drop a module under `backend/app/data_sources/` and merge in `routers/snapshot.py`.
- Real ML: replace `backend/app/analytics/forecast.py::seasonal_forecast` (same return shape).
- Postgres / TimescaleDB: swap `backend/app/data_sources/csv_loader.py::load_history` behind a repo interface.
- Scenario planner: add `backend/app/routers/scenarios.py` and a panel on the dashboard.
- Multi-basin: register new `Basin`s in `backend/app/config.py`; the frontend already keys off `/api/basins`.
