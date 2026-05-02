"""GET /api/forecast/{basin_id} — seasonal-naive forecast across metrics."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..analytics.forecast import seasonal_forecast
from ..config import BASINS
from ..data_sources.csv_loader import load_history

router = APIRouter()


@router.get("/forecast/{basin_id}")
def forecast(basin_id: str, horizon_months: int = 6) -> dict:
    if basin_id not in BASINS:
        raise HTTPException(404, f"Unknown basin: {basin_id}")
    horizon_months = max(1, min(horizon_months, 12))
    history = load_history()
    return {
        "basin_id": basin_id,
        "model": "seasonal-naive-v0",
        "horizon_months": horizon_months,
        **seasonal_forecast(history, horizons_months=horizon_months),
    }
