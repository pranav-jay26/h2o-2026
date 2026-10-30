"""GET /api/reservoirs — markers + current stats for every basin in the registry.

Used by the map. Live CDEC reservoir storage is fetched in parallel; basins
without a CSV history get a simple capacity-band risk level so they still
render meaningfully on the map.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter

from ..analytics.release_risk import ReleaseInputs, evaluate
from ..analytics.risk import compute_risk
from ..analytics.stats import value_percentile
from ..config import BASINS, Basin
from ..data_sources.cdec import ReservoirReading, fetch_reservoir
from ..data_sources.csv_loader import load_history
from ..data_sources.nasa_power import MetSummary, fetch_met_summary
from ..data_sources.noaa_forecast import QPFForecast, fetch_qpf

router = APIRouter()


@router.get("/reservoirs")
async def reservoirs() -> dict:
    history = load_history()
    basin_list = list(BASINS.values())

    # Fetch CDEC + POWER + NOAA for every basin in parallel. Caches keep this
    # fast on subsequent calls.
    cdec_task = asyncio.gather(*(fetch_reservoir(b) for b in basin_list))
    power_task = asyncio.gather(*(fetch_met_summary(b.lat, b.lon) for b in basin_list))
    qpf_task = asyncio.gather(*(fetch_qpf(b.lat, b.lon) for b in basin_list))
    cdec_readings, power_summaries, qpf_forecasts = await asyncio.gather(cdec_task, power_task, qpf_task)

    items = [
        _marker(b, cdec, met_, qpf, history)
        for b, cdec, met_, qpf in zip(basin_list, cdec_readings, power_summaries, qpf_forecasts)
    ]
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "reservoirs": items,
    }


def _marker(
    basin: Basin,
    reading: ReservoirReading | None,
    met: MetSummary | None,
    qpf: QPFForecast | None,
    history,
) -> dict:
    if reading is not None:
        pct = reading.percent_capacity
        storage_af = reading.storage_af
        as_of = reading.obs_date
        source = "cdec:live"
    else:
        # Fallback for basins without live data: use latest CSV row only if this is the
        # anchored historical basin; otherwise mark as unknown.
        if basin.has_history:
            row = history.iloc[-1]
            pct = float(row["reservoir"])
            storage_af = round(basin.capacity_af * pct / 100.0)
            as_of = row["date"].isoformat()
            source = "csv:challenge.csv"
        else:
            pct = None
            storage_af = None
            as_of = None
            source = "unavailable"

    risk_level = _risk_level(basin, pct, history)

    snow_pctile = None
    if basin.has_history:
        month = datetime.now(timezone.utc).month
        latest_snow = float(history.iloc[-1]["snowpack"])
        snow_pctile = value_percentile(history, "snowpack", month, latest_snow)

    release = evaluate(
        ReleaseInputs(
            storage_pct=pct,
            observed_pct_of_normal_precip=met.pct_of_normal_precip if met else None,
            qpf_7d_in=qpf.next_7d_total_in if qpf else None,
            snowpack_percentile=snow_pctile,
            forecast_temp_c_avg=qpf.forecast_temp_c_avg if qpf else None,
            climatology_temp_c=met.current_month_climo_temp_c if met else None,
        )
    )

    return {
        "id": basin.id,
        "name": basin.name,
        "watershed": basin.watershed,
        "cdec_station": basin.cdec_station,
        "lat": basin.lat,
        "lon": basin.lon,
        "capacity_af": basin.capacity_af,
        "current": {
            "percent_capacity": pct,
            "storage_af": storage_af,
            "as_of": as_of,
            "source": source,
        },
        "risk_level": risk_level,
        "release_risk": release,
        "met": _met_brief(met),
        "forecast": _qpf_brief(qpf),
        "has_history": basin.has_history,
    }


def _met_brief(m: MetSummary | None) -> dict | None:
    if m is None:
        return None
    return {
        "observed_30d_precip_in": m.observed_30d_precip_in,
        "pct_of_normal_precip": m.pct_of_normal_precip,
        "temp_anomaly_c": m.temp_anomaly_c,
    }


def _qpf_brief(q: QPFForecast | None) -> dict | None:
    if q is None:
        return None
    return {
        "next_7d_total_in": q.next_7d_total_in,
        "forecast_temp_c_avg": q.forecast_temp_c_avg,
    }


def _risk_level(basin: Basin, pct: float | None, history) -> str:
    """Reservoirs with a CSV history use the percentile-based composite score; the
    rest use a flat capacity-band rule so the map still gets a useful color."""
    if pct is None:
        return "unknown"
    if basin.has_history:
        month = datetime.now(timezone.utc).month
        p = value_percentile(history, "reservoir", month, pct)
        risk = compute_risk({"reservoir": p})
        return risk["level"]
    if pct >= 70:
        return "green"
    if pct >= 45:
        return "amber"
    return "red"
