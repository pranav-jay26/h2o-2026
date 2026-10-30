"""NASA POWER daily-point client (MERRA-2 reanalysis + CERES).

POWER is **observational, not a forecast** — we use it for two things:

1. Observed last-N days of precipitation and 2-m temperature at a basin centroid.
2. Long-term monthly climatology, used to express the recent observation as
   "% of normal" for the same calendar period.

Endpoints (free, no auth):
- daily:       https://power.larc.nasa.gov/api/temporal/daily/point
- climatology: https://power.larc.nasa.gov/api/temporal/climatology/point

Units returned by POWER:
- PRECTOTCORR: mm/day   (we surface mm and inches)
- T2M:         °C
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

log = logging.getLogger(__name__)

POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_CLIMO_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"

PARAMETERS = "PRECTOTCORR,T2M"
COMMUNITY = "AG"

# Cache TTLs.
DAILY_TTL_S = 6 * 60 * 60       # observed data updates ~daily; refresh every 6h
CLIMATOLOGY_TTL_S = 30 * 24 * 60 * 60  # climatology is effectively static

# POWER returns -999 for missing values.
MISSING = -999.0

MM_PER_INCH = 25.4
MONTH_NAMES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


@dataclass
class MetSummary:
    lat: float
    lon: float
    observed_30d_precip_mm: float
    observed_30d_precip_in: float
    climatology_30d_precip_mm: float
    pct_of_normal_precip: float | None        # observed / climatology * 100
    observed_7d_temp_c: float
    climatology_temp_c: float                 # weighted to the observed 7d window
    temp_anomaly_c: float                     # observed - window_climatology
    current_month_climo_temp_c: float | None  # this calendar month's normal — used to
                                              # compare against NOAA forecast temps.
    observed_window: tuple[str, str]          # (start_iso, end_iso) — POWER coverage
    fetched_at: str


_daily_cache: dict[tuple[float, float], tuple[float, dict]] = {}
_climo_cache: dict[tuple[float, float], tuple[float, dict]] = {}


async def fetch_met_summary(lat: float, lon: float) -> MetSummary | None:
    """Pull observed last-60d daily values + climatology and summarize.

    Returns None on network failure. Caller should degrade gracefully.
    """
    daily = await _fetch_daily(lat, lon, days_back=60)
    climo = await _fetch_climatology(lat, lon)
    if daily is None or climo is None:
        return None

    # Daily values are dicts keyed by `YYYYMMDD`. Pick the most recent 30 days
    # of valid observations for precip; most recent 7 days for temperature.
    precip_series = _series(daily, "PRECTOTCORR")
    temp_series = _series(daily, "T2M")

    if not precip_series:
        return None

    end_key = max(precip_series)
    start_key = min(precip_series)

    last_30 = _tail(precip_series, n=30)
    last_7_temp = _tail(temp_series, n=7)

    obs_30d_mm = round(sum(last_30.values()), 2)
    obs_30d_in = round(obs_30d_mm / MM_PER_INCH, 2)
    obs_7d_temp = round(_mean(last_7_temp.values()), 2) if last_7_temp else 0.0

    # Climatology baseline: weight POWER's per-month daily means by how many days
    # of the *observed window* fell in each month, then × 30. This avoids the
    # off-by-one where today's month doesn't match the window (POWER trails ~2d).
    climo_precip_per_day = _weighted_daily_climatology(climo.get("PRECTOTCORR", {}), last_30.keys())
    climo_30d_mm = round(climo_precip_per_day * 30.0, 2)
    pct_of_normal = round(100.0 * obs_30d_mm / climo_30d_mm, 1) if climo_30d_mm > 0 else None

    climo_temp_c = _weighted_daily_climatology(climo.get("T2M", {}), last_7_temp.keys()) if last_7_temp else 0.0
    temp_anomaly = round(obs_7d_temp - climo_temp_c, 2)

    today_month = MONTH_NAMES[datetime.now(timezone.utc).date().month - 1]
    current_month_climo = climo.get("T2M", {}).get(today_month)
    current_month_climo_c = float(current_month_climo) if isinstance(current_month_climo, (int, float)) else None

    return MetSummary(
        lat=lat,
        lon=lon,
        observed_30d_precip_mm=obs_30d_mm,
        observed_30d_precip_in=obs_30d_in,
        climatology_30d_precip_mm=climo_30d_mm,
        pct_of_normal_precip=pct_of_normal,
        observed_7d_temp_c=obs_7d_temp,
        climatology_temp_c=round(climo_temp_c, 2),
        temp_anomaly_c=temp_anomaly,
        current_month_climo_temp_c=round(current_month_climo_c, 2) if current_month_climo_c is not None else None,
        observed_window=(_format_key(start_key), _format_key(end_key)),
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


async def _fetch_daily(lat: float, lon: float, days_back: int = 60) -> dict | None:
    key = (round(lat, 4), round(lon, 4))
    cached = _daily_cache.get(key)
    if cached and time.time() - cached[0] < DAILY_TTL_S:
        return cached[1]

    end = date.today() - timedelta(days=2)  # POWER usually trails today by ~2 days
    start = end - timedelta(days=days_back)
    params = {
        "parameters": PARAMETERS,
        "community": COMMUNITY,
        "longitude": str(lon),
        "latitude": str(lat),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(POWER_DAILY_URL, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        log.warning("NASA POWER daily fetch failed for %s,%s: %s", lat, lon, e)
        return None

    parameters = payload.get("properties", {}).get("parameter", {})
    if not parameters:
        return None
    _daily_cache[key] = (time.time(), parameters)
    return parameters


async def _fetch_climatology(lat: float, lon: float) -> dict | None:
    key = (round(lat, 4), round(lon, 4))
    cached = _climo_cache.get(key)
    if cached and time.time() - cached[0] < CLIMATOLOGY_TTL_S:
        return cached[1]

    params = {
        "parameters": PARAMETERS,
        "community": COMMUNITY,
        "longitude": str(lon),
        "latitude": str(lat),
        "format": "JSON",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(POWER_CLIMO_URL, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        log.warning("NASA POWER climatology fetch failed for %s,%s: %s", lat, lon, e)
        return None

    parameters = payload.get("properties", {}).get("parameter", {})
    if not parameters:
        return None
    _climo_cache[key] = (time.time(), parameters)
    return parameters


def _series(daily: dict, key: str) -> dict[str, float]:
    raw = daily.get(key, {})
    return {k: float(v) for k, v in raw.items() if isinstance(v, (int, float)) and float(v) > MISSING}


def _tail(series: dict[str, float], n: int) -> dict[str, float]:
    if not series:
        return {}
    keys = sorted(series.keys())[-n:]
    return {k: series[k] for k in keys}


def _mean(values) -> float:
    vs = list(values)
    return sum(vs) / len(vs) if vs else 0.0


def _format_key(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"
    return yyyymmdd


def _weighted_daily_climatology(monthly_means: dict, day_keys) -> float:
    """Average POWER's per-month daily climatology weighted by how many of the
    given `day_keys` (YYYYMMDD strings) fell in each month."""
    if not monthly_means or not day_keys:
        return 0.0
    counts: dict[str, int] = {}
    for k in day_keys:
        if len(k) >= 6 and k.isdigit():
            month_idx = int(k[4:6]) - 1
            if 0 <= month_idx < 12:
                month_name = MONTH_NAMES[month_idx]
                counts[month_name] = counts.get(month_name, 0) + 1
    total_days = sum(counts.values())
    if total_days == 0:
        return 0.0
    weighted = 0.0
    for month, n in counts.items():
        v = monthly_means.get(month)
        if isinstance(v, (int, float)):
            weighted += float(v) * n
    return weighted / total_days
