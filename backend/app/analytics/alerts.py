"""Threshold-based alert rules over the latest observation + recent trend."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .stats import value_percentile


def _trend(history: pd.DataFrame, metric: str, lookback: int = 3) -> float:
    tail = history[metric].tail(lookback + 1).to_numpy()
    if len(tail) < 2:
        return 0.0
    return float(tail[-1] - tail[0])


def evaluate_alerts(history: pd.DataFrame, live_overrides: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Return triggered alerts. `live_overrides` may replace latest values (e.g. live reservoir)."""
    latest = history.iloc[-1].copy()
    if live_overrides:
        for k, v in live_overrides.items():
            if k in latest.index:
                latest[k] = v

    month = int(latest["month"])
    alerts: list[dict[str, Any]] = []

    for metric in ("snowpack", "precip", "reservoir"):
        value = float(latest[metric])
        pct = value_percentile(history, metric, month, value)
        trend = _trend(history, metric)

        if pct < 10:
            alerts.append(
                _make(
                    metric,
                    "red",
                    f"{metric.title()} at p{pct} for this month — bottom 10% historically.",
                    value=value,
                    threshold=10,
                    window="month-of-year",
                    action=_action(metric, "red"),
                )
            )
        elif pct < 25:
            alerts.append(
                _make(
                    metric,
                    "amber",
                    f"{metric.title()} at p{pct} for this month — below 25th percentile.",
                    value=value,
                    threshold=25,
                    window="month-of-year",
                    action=_action(metric, "amber"),
                )
            )

        if metric == "reservoir" and trend < -5:
            alerts.append(
                _make(
                    "reservoir",
                    "amber",
                    f"Reservoir down {abs(trend):.1f} percentage points over last 3 months.",
                    value=value,
                    threshold=-5,
                    window="3 months",
                    action="Tighten irrigation scheduling and review crop staging.",
                )
            )
        if metric == "snowpack" and trend < -20 and month in (3, 4, 5):
            alerts.append(
                _make(
                    "snowpack",
                    "amber",
                    f"Snowpack melting fast: down {abs(trend):.0f} units over 3 months during peak melt.",
                    value=value,
                    threshold=-20,
                    window="3 months",
                    action="Plan for earlier-than-usual runoff and reservoir peak.",
                )
            )
    return alerts


def _make(metric: str, level: str, why: str, **extra: Any) -> dict[str, Any]:
    return {"metric": metric, "level": level, "why": why, **extra}


def _action(metric: str, level: str) -> str:
    if metric == "reservoir":
        return "Reduce non-critical irrigation; expect tighter water deliveries." if level == "red" else "Review water budget for the next 30 days."
    if metric == "snowpack":
        return "Assume below-normal spring runoff; conserve carry-over storage." if level == "red" else "Watch CNRFC seasonal outlook updates closely."
    if metric == "precip":
        return "Plan for drought-year conditions; pre-irrigate where feasible." if level == "red" else "Track upcoming storm forecasts; defer planting if possible."
    return "Review water plan."
