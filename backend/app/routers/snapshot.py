"""GET /api/snapshot/{basin_id} — current state + risk level."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException

from ..analytics.alerts import evaluate_alerts
from ..analytics.risk import compute_risk, explain_drivers
from ..analytics.stats import value_percentile
from ..config import BASINS
from ..data_sources.cdec import fetch_reservoir
from ..data_sources.csv_loader import load_history

router = APIRouter()


@router.get("/snapshot/{basin_id}")
async def snapshot(basin_id: str) -> dict:
    basin = BASINS.get(basin_id)
    if not basin:
        raise HTTPException(404, f"Unknown basin: {basin_id}")

    history = load_history()
    latest = history.iloc[-1]
    csv_month = int(latest["month"])
    csv_as_of = latest["date"].isoformat()

    live = await fetch_reservoir(basin)

    snow = _metric_payload(history, "snowpack", float(latest["snowpack"]), csv_month, source="csv:challenge.csv", as_of=csv_as_of)
    precip = _metric_payload(history, "precip", float(latest["precip"]), csv_month, source="csv:challenge.csv", as_of=csv_as_of)

    if live is not None:
        live_month = _month_from_obs(live.obs_date) or csv_month
        reservoir = _metric_payload(
            history,
            "reservoir",
            live.percent_capacity,
            live_month,
            source="cdec:live",
            as_of=live.obs_date,
            extras={"storage_af": live.storage_af},
        )
    else:
        reservoir = _metric_payload(
            history,
            "reservoir",
            float(latest["reservoir"]),
            csv_month,
            source="csv:challenge.csv",
            as_of=csv_as_of,
        )

    percentiles = {
        "snowpack": snow["percentile"],
        "precip": precip["percentile"],
        "reservoir": reservoir["percentile"],
    }
    risk = compute_risk(percentiles)
    risk["explanations"] = explain_drivers(risk["drivers"])

    overrides = {"reservoir": live.percent_capacity} if live else None
    alerts = evaluate_alerts(history, live_overrides=overrides)

    return {
        "basin": {
            "id": basin.id,
            "name": basin.name,
            "watershed": basin.watershed,
            "cdec_station": basin.cdec_station,
            "capacity_af": basin.capacity_af,
        },
        "as_of": datetime.now(timezone.utc).isoformat(),
        "metrics": {"snowpack": snow, "precip": precip, "reservoir": reservoir},
        "risk": risk,
        "alerts": alerts,
        "data_freshness": {
            "csv_latest": csv_as_of,
            "cdec_live": live.fetched_at if live else None,
            "cdec_status": "ok" if live else "unavailable",
        },
    }


def _metric_payload(
    history: pd.DataFrame,
    metric: str,
    value: float,
    compare_month: int,
    *,
    source: str,
    as_of: str,
    extras: dict | None = None,
) -> dict:
    series = history.loc[history["month"] == compare_month, metric].dropna()
    mean = float(series.mean()) if len(series) else value
    std = float(series.std(ddof=0)) if len(series) > 1 else 0.0
    payload = {
        "value": round(value, 2),
        "month_mean": round(mean, 2),
        "anomaly": round(value - mean, 2),
        "z": round((value - mean) / std, 2) if std > 0 else 0.0,
        "percentile": value_percentile(history, metric, compare_month, value),
        "compare_month": compare_month,
        "source": source,
        "as_of": as_of,
    }
    if extras:
        payload["extras"] = extras
    return payload


def _month_from_obs(obs_date: str) -> int | None:
    """CDEC obsDate may use unpadded month/day (e.g. `2026-5-2 00:00`); pandas handles it."""
    if not obs_date:
        return None
    try:
        return int(pd.to_datetime(obs_date).month)
    except Exception:
        return None
