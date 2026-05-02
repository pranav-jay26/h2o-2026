"""CDEC live feed for reservoir storage.

Fetches daily reservoir storage (sensor 15) from CDEC's JSON servlet for the
configured station and converts to percent-of-capacity. Falls back to None on
network failure so callers can degrade gracefully to historical CSV.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import CDEC_CACHE_TTL_S, Basin

log = logging.getLogger(__name__)

CDEC_URL = "https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet"
CDEC_RESERVOIR_STORAGE_SENSOR = 15  # Reservoir storage, acre-feet


@dataclass
class ReservoirReading:
    station: str
    storage_af: float
    percent_capacity: float
    obs_date: str  # ISO8601
    fetched_at: str  # ISO8601


_cache: dict[str, tuple[float, ReservoirReading]] = {}


async def fetch_reservoir(basin: Basin, lookback_days: int = 14) -> ReservoirReading | None:
    """Most recent daily reservoir storage reading for `basin`. Returns None on failure."""
    cached = _cache.get(basin.cdec_station)
    if cached and time.time() - cached[0] < CDEC_CACHE_TTL_S:
        return cached[1]

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=lookback_days)
    params = {
        "Stations": basin.cdec_station,
        "SensorNums": CDEC_RESERVOIR_STORAGE_SENSOR,
        "dur_code": "D",
        "Start": start.isoformat(),
        "End": end.isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(CDEC_URL, params=params)
            r.raise_for_status()
            payload: list[dict[str, Any]] = r.json()
    except Exception as e:
        log.warning("CDEC fetch failed for %s: %s", basin.cdec_station, e)
        return None

    latest = _pick_latest_valid(payload)
    if latest is None:
        return None

    storage_af = float(latest["value"])
    reading = ReservoirReading(
        station=basin.cdec_station,
        storage_af=storage_af,
        percent_capacity=round(100.0 * storage_af / basin.capacity_af, 2),
        obs_date=str(latest.get("obsDate") or latest.get("date") or ""),
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    _cache[basin.cdec_station] = (time.time(), reading)
    return reading


def _pick_latest_valid(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """CDEC returns -9999 / blank for missing values; pick the most recent valid one."""
    valid = []
    for row in rows:
        val = row.get("value")
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v <= 0 or v > 1e8:
            continue
        valid.append(row)
    if not valid:
        return None
    return sorted(valid, key=lambda r: r.get("obsDate") or r.get("date") or "")[-1]
