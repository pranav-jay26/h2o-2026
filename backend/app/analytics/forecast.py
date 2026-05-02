"""Seasonal-naive forecast with a simple uncertainty band.

The CSV is monthly snapshots, so we forecast monthly: the next N months use
the historical mean for each calendar month, with the band = mean ± 1 std.
A short-term 7-day point estimate is interpolated linearly between the latest
observation and the next month's mean.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from .stats import METRICS


def _month_norms(history: pd.DataFrame, metric: str) -> dict[int, tuple[float, float]]:
    g = history.groupby("month")[metric]
    return {int(m): (float(g.mean()[m]), float(g.std(ddof=0)[m] or 0.0)) for m in g.groups}


def seasonal_forecast(history: pd.DataFrame, horizons_months: int = 6) -> dict:
    """Per-metric monthly forecast for the next `horizons_months` after the latest row."""
    latest = history.iloc[-1]
    last_date: pd.Timestamp = latest["date"]

    out: dict = {"as_of": last_date.isoformat(), "metrics": {}}
    for metric in METRICS:
        norms = _month_norms(history, metric)
        points = []
        cursor = last_date
        last_value = float(latest[metric])
        for i in range(1, horizons_months + 1):
            cursor = (cursor + pd.offsets.MonthBegin(1)).normalize()
            mean, std = norms.get(cursor.month, (last_value, 0.0))
            # Pull the first step partway toward the seasonal mean to avoid a jump.
            blended_mean = 0.5 * last_value + 0.5 * mean if i == 1 else mean
            points.append(
                {
                    "date": cursor.date().isoformat(),
                    "mean": round(blended_mean, 2),
                    "lower": round(max(0.0, blended_mean - std), 2),
                    "upper": round(blended_mean + std, 2),
                }
            )
        # 7-day point estimate: linear blend between last obs and next-month mean.
        next_mean = points[0]["mean"] if points else last_value
        seven_day = round(last_value + (next_mean - last_value) * (7 / 30), 2)
        out["metrics"][metric] = {
            "latest": last_value,
            "seven_day": seven_day,
            "monthly": points,
        }
    return out
