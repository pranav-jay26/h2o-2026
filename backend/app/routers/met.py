"""GET /api/met/{basin_id} — meteorological + release-risk for one basin.

Combines NASA POWER (observed precip + temp, climatology) and NOAA NWS QPF.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..analytics.release_risk import ReleaseInputs, evaluate
from ..analytics.stats import value_percentile
from ..config import BASINS, Basin
from ..data_sources.cdec import fetch_reservoir
from ..data_sources.csv_loader import load_history
from ..data_sources.nasa_power import fetch_met_summary
from ..data_sources.noaa_forecast import fetch_qpf

router = APIRouter()


@router.get("/met/{basin_id}")
async def met(basin_id: str) -> dict:
    basin = BASINS.get(basin_id)
    if not basin:
        raise HTTPException(404, f"Unknown basin: {basin_id}")

    history = load_history()
    met_, qpf, reservoir_live = await asyncio.gather(
        fetch_met_summary(basin.lat, basin.lon),
        fetch_qpf(basin.lat, basin.lon),
        fetch_reservoir(basin),
    )

    storage_pct = reservoir_live.percent_capacity if reservoir_live else None
    snow_pct = None
    if basin.has_history:
        month = datetime.now(timezone.utc).month
        latest_snow = float(history.iloc[-1]["snowpack"])
        snow_pct = value_percentile(history, "snowpack", month, latest_snow)

    inputs = ReleaseInputs(
        storage_pct=storage_pct,
        observed_pct_of_normal_precip=met_.pct_of_normal_precip if met_ else None,
        qpf_7d_in=qpf.next_7d_total_in if qpf else None,
        snowpack_percentile=snow_pct,
        forecast_temp_c_avg=qpf.forecast_temp_c_avg if qpf else None,
        climatology_temp_c=met_.current_month_climo_temp_c if met_ else None,
    )
    risk = evaluate(inputs)

    return {
        "basin": _basin_payload(basin),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "observed": _met_payload(met_),
        "forecast": _qpf_payload(qpf),
        "release_risk": risk,
        "data_freshness": {
            "nasa_power": met_.fetched_at if met_ else None,
            "noaa_qpf": qpf.fetched_at if qpf else None,
            "cdec": reservoir_live.fetched_at if reservoir_live else None,
        },
    }


def _basin_payload(b: Basin) -> dict:
    return {"id": b.id, "name": b.name, "watershed": b.watershed, "lat": b.lat, "lon": b.lon}


def _met_payload(m) -> dict | None:
    if m is None:
        return None
    return {
        "observed_30d_precip_mm": m.observed_30d_precip_mm,
        "observed_30d_precip_in": m.observed_30d_precip_in,
        "climatology_30d_precip_mm": m.climatology_30d_precip_mm,
        "pct_of_normal_precip": m.pct_of_normal_precip,
        "observed_7d_temp_c": m.observed_7d_temp_c,
        "climatology_temp_c": m.climatology_temp_c,
        "temp_anomaly_c": m.temp_anomaly_c,
        "current_month_climo_temp_c": m.current_month_climo_temp_c,
        "observed_window": list(m.observed_window),
        "source": "nasa-power:daily+climatology",
    }


def _qpf_payload(q) -> dict | None:
    if q is None:
        return None
    return {
        "office": q.office,
        "grid_x": q.grid_x,
        "grid_y": q.grid_y,
        "next_7d_total_mm": q.next_7d_total_mm,
        "next_7d_total_in": q.next_7d_total_in,
        "by_day": q.by_day,
        "forecast_temp_c_avg": q.forecast_temp_c_avg,
        "source": "noaa-nws:gridpoint",
    }
