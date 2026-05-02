"""FastAPI entrypoint. Run with: `uvicorn app.main:app --reload --port 8000` from backend/."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import BASINS
from .routers import alerts, forecast, snapshot, timeseries

app = FastAPI(title="H2O Predictive Water Intelligence", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(snapshot.router, prefix="/api")
app.include_router(timeseries.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/basins")
def list_basins() -> dict:
    return {
        "basins": [
            {
                "id": b.id,
                "name": b.name,
                "watershed": b.watershed,
                "cdec_station": b.cdec_station,
                "capacity_af": b.capacity_af,
            }
            for b in BASINS.values()
        ]
    }
