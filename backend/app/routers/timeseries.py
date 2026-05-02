"""GET /api/timeseries/{basin_id}/{metric} — historical values + per-month bands."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..analytics.stats import METRICS, monthly_bands
from ..config import BASINS
from ..data_sources.csv_loader import load_history

router = APIRouter()


@router.get("/timeseries/{basin_id}/{metric}")
def timeseries(basin_id: str, metric: str) -> dict:
    if basin_id not in BASINS:
        raise HTTPException(404, f"Unknown basin: {basin_id}")
    if metric not in METRICS:
        raise HTTPException(400, f"Unknown metric: {metric}. Valid: {METRICS}")

    history = load_history()
    bands = monthly_bands(history, metric)

    band_lookup = {int(row["month"]): row.to_dict() for _, row in bands.iterrows()}
    points = []
    for _, row in history.iterrows():
        month_band = band_lookup.get(int(row["month"]), {})
        points.append(
            {
                "date": row["date"].date().isoformat(),
                "value": float(row[metric]),
                "p10": float(month_band.get("p10", 0)),
                "p25": float(month_band.get("p25", 0)),
                "p50": float(month_band.get("p50", 0)),
                "p75": float(month_band.get("p75", 0)),
                "p90": float(month_band.get("p90", 0)),
                "month_mean": float(month_band.get("mean", 0)),
            }
        )
    return {
        "basin_id": basin_id,
        "metric": metric,
        "points": points,
        "monthly_bands": bands.to_dict(orient="records"),
    }
