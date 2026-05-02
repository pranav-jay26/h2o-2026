# Backend — H2O Predictive Water Intelligence

FastAPI sidecar that loads the historical CSV, pulls live reservoir storage
from CDEC for Shasta Lake, computes per-month percentile bands, a composite
risk score, threshold alerts, and a seasonal-naive forecast.

## Run

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Dependencies live in `pyproject.toml`; `uv sync` creates `.venv/` and installs them.

## Endpoints

- `GET /api/health`
- `GET /api/basins`
- `GET /api/snapshot/{basin_id}` — current state, risk, alerts (uses live CDEC if reachable)
- `GET /api/timeseries/{basin_id}/{metric}` — historical points + per-month percentile bands
- `GET /api/forecast/{basin_id}?horizon_months=6` — seasonal-naive forecast with uncertainty band
- `GET /api/alerts/{basin_id}` — triggered threshold alerts

`basin_id`: `shasta`. `metric`: `snowpack` | `precip` | `reservoir`.

## Layout

- `app/config.py` — basin registry, risk thresholds, weights.
- `app/data_sources/csv_loader.py` — historical CSV loader.
- `app/data_sources/cdec.py` — CDEC live feed (sensor 15, daily) with TTL cache + graceful fallback.
- `app/analytics/stats.py` — percentile bands and percentile lookups.
- `app/analytics/forecast.py` — monthly seasonal-naive forecast with uncertainty band.
- `app/analytics/risk.py` — composite percentile-based risk score.
- `app/analytics/alerts.py` — threshold rules with `why` + `action`.
- `app/routers/` — one file per endpoint group.

## Future hooks

- Swap `csv_loader` for a Postgres/Timescale-backed repo.
- Replace `seasonal_forecast` with a learned model behind the same interface.
- Add more `data_sources/` (CNRFC, NASA SMAP) and merge in `analytics/`.
- Add `routers/scenarios.py` for what-if simulations.
