"""NOAA NWS gridpoint client for 7-day quantitative precipitation forecast.

Two-step protocol:
1. GET /points/{lat},{lon}        → returns the forecast office + grid (X, Y).
2. GET /gridpoints/{office}/{X},{Y} → returns gridded forecast values, including
   `quantitativePrecipitation` (mm) and `temperature` (°C) over time intervals.

Free, no auth. NWS asks every client to send a descriptive User-Agent.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

log = logging.getLogger(__name__)

POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"

# A descriptive User-Agent is requested by NWS. They use it to contact you if
# something goes wrong with your traffic; pick a string that identifies the app.
USER_AGENT = "h2o-water-intel/0.1 (hackathon demo; contact: jayakumar.pranav@gmail.com)"

GRIDPOINT_TTL_S = 30 * 24 * 60 * 60   # office/X/Y for a fixed lat/lon is stable
FORECAST_TTL_S = 30 * 60              # forecast updates ~hourly

MM_PER_INCH = 25.4

_gridpoint_cache: dict[tuple[float, float], tuple[float, dict]] = {}
_forecast_cache: dict[tuple[str, int, int], tuple[float, dict]] = {}


@dataclass
class QPFForecast:
    office: str
    grid_x: int
    grid_y: int
    next_7d_total_mm: float
    next_7d_total_in: float
    by_day: list[dict]                # [{"date": "2026-05-03", "precip_mm": float, "precip_in": float}]
    forecast_temp_c_avg: float | None # mean of forecast 2-m temps over the next 7d
    fetched_at: str


async def fetch_qpf(lat: float, lon: float, horizon_days: int = 7) -> QPFForecast | None:
    grid = await _fetch_gridpoint(lat, lon)
    if grid is None:
        return None
    office = grid["gridId"]
    gx = grid["gridX"]
    gy = grid["gridY"]

    payload = await _fetch_forecast(office, gx, gy)
    if payload is None:
        return None

    qpf_values = payload.get("quantitativePrecipitation", {}).get("values", [])
    temp_values = payload.get("temperature", {}).get("values", [])

    horizon_end = datetime.now(timezone.utc) + timedelta(days=horizon_days)
    qpf_by_day: dict[str, float] = {}
    for entry in qpf_values:
        valid = _parse_iso(entry.get("validTime"))
        if valid is None or valid["start"] > horizon_end:
            continue
        day_key = valid["start"].date().isoformat()
        qpf_by_day[day_key] = qpf_by_day.get(day_key, 0.0) + float(entry.get("value") or 0.0)

    by_day_sorted = sorted(qpf_by_day.items())[:horizon_days]
    by_day = [
        {"date": d, "precip_mm": round(mm, 2), "precip_in": round(mm / MM_PER_INCH, 2)}
        for d, mm in by_day_sorted
    ]
    total_mm = round(sum(d["precip_mm"] for d in by_day), 2)
    total_in = round(total_mm / MM_PER_INCH, 2)

    temps_c: list[float] = []
    for entry in temp_values:
        valid = _parse_iso(entry.get("validTime"))
        if valid is None or valid["start"] > horizon_end:
            continue
        v = entry.get("value")
        if v is not None:
            temps_c.append(float(v))
    forecast_temp_avg = round(sum(temps_c) / len(temps_c), 2) if temps_c else None

    return QPFForecast(
        office=office,
        grid_x=gx,
        grid_y=gy,
        next_7d_total_mm=total_mm,
        next_7d_total_in=total_in,
        by_day=by_day,
        forecast_temp_c_avg=forecast_temp_avg,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


async def _fetch_gridpoint(lat: float, lon: float) -> dict | None:
    key = (round(lat, 4), round(lon, 4))
    cached = _gridpoint_cache.get(key)
    if cached and time.time() - cached[0] < GRIDPOINT_TTL_S:
        return cached[1]

    url = POINTS_URL.format(lat=lat, lon=lon)
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"}) as client:
            r = await client.get(url)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        log.warning("NOAA points lookup failed for %s,%s: %s", lat, lon, e)
        return None

    props = payload.get("properties", {})
    grid = {
        "gridId": props.get("gridId"),
        "gridX": props.get("gridX"),
        "gridY": props.get("gridY"),
    }
    if not all(grid.values()):
        return None
    _gridpoint_cache[key] = (time.time(), grid)
    return grid


async def _fetch_forecast(office: str, gx: int, gy: int) -> dict | None:
    key = (office, gx, gy)
    cached = _forecast_cache.get(key)
    if cached and time.time() - cached[0] < FORECAST_TTL_S:
        return cached[1]

    url = f"https://api.weather.gov/gridpoints/{office}/{gx},{gy}"
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"}) as client:
            r = await client.get(url)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        log.warning("NOAA gridpoint forecast failed for %s/%s,%s: %s", office, gx, gy, e)
        return None

    properties = payload.get("properties", {})
    if not properties:
        return None
    _forecast_cache[key] = (time.time(), properties)
    return properties


def _parse_iso(iso_interval: str | None) -> dict | None:
    """NOAA's `validTime` is ISO8601 with a duration suffix: `2026-05-03T00:00:00+00:00/PT6H`."""
    if not iso_interval or "/" not in iso_interval:
        return None
    start_str, _ = iso_interval.split("/", 1)
    try:
        return {"start": datetime.fromisoformat(start_str)}
    except ValueError:
        return None
