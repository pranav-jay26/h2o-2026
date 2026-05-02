"""Composite water-stress risk score.

Each metric contributes points based on where its current value sits in the
historical month-of-year distribution. Sum is weighted by `METRIC_WEIGHTS`
to a 0..100 scale, then bucketed into green/amber/red bands.
"""

from __future__ import annotations

from typing import Iterable

from ..config import METRIC_WEIGHTS, RISK_BANDS


def _points_for_percentile(p: float) -> int:
    if p < RISK_BANDS["red"]:
        return 100
    if p < RISK_BANDS["amber"]:
        return 65
    if p < RISK_BANDS["watch"]:
        return 30
    return 5


def _level_for_score(score: float) -> str:
    if score >= 65:
        return "red"
    if score >= 30:
        return "amber"
    return "green"


def compute_risk(percentiles: dict[str, float]) -> dict:
    """`percentiles` keyed by metric name -> empirical percentile in [0,100]."""
    drivers = []
    weighted_sum = 0.0
    weight_total = 0.0
    for metric, weight in METRIC_WEIGHTS.items():
        if metric not in percentiles:
            continue
        p = percentiles[metric]
        pts = _points_for_percentile(p)
        weighted_sum += weight * pts
        weight_total += weight
        drivers.append({"metric": metric, "percentile": p, "points": pts, "weight": weight})

    score = round(weighted_sum / weight_total, 1) if weight_total else 0.0
    return {
        "score": score,
        "level": _level_for_score(score),
        "drivers": sorted(drivers, key=lambda d: -d["points"]),
    }


def explain_drivers(drivers: Iterable[dict]) -> list[str]:
    """Plain-language reasons for the risk level."""
    msgs = []
    for d in drivers:
        p = d["percentile"]
        m = d["metric"]
        if p < 10:
            msgs.append(f"{m} is in the bottom 10% of historical values for this month (p={p}).")
        elif p < 25:
            msgs.append(f"{m} is below the 25th percentile for this month (p={p}).")
        elif p < 50:
            msgs.append(f"{m} is below the historical median for this month (p={p}).")
    return msgs
