"""GET /api/alerts/{basin_id} — currently triggered threshold alerts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..analytics.alerts import evaluate_alerts
from ..config import BASINS
from ..data_sources.cdec import fetch_reservoir
from ..data_sources.csv_loader import load_history

router = APIRouter()


@router.get("/alerts/{basin_id}")
async def alerts(basin_id: str) -> dict:
    basin = BASINS.get(basin_id)
    if not basin:
        raise HTTPException(404, f"Unknown basin: {basin_id}")
    history = load_history()
    live = await fetch_reservoir(basin)
    overrides = {"reservoir": live.percent_capacity} if live else None
    items = evaluate_alerts(history, live_overrides=overrides)
    return {"basin_id": basin_id, "count": len(items), "alerts": items}
