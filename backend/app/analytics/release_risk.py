"""Composite release-likelihood signal for the Release Anticipation feature.

Combines reservoir storage, recent observed precip vs. climatology (NASA POWER),
forecast precipitation (NOAA NWS QPF), and a melt-risk proxy (snowpack percentile
or 7-day forecast temperature anomaly).

The rule is intentionally transparent and rule-based — users see *why* a
release is plausible. This is advisory; it does not predict actual operator
decisions, which involve flood-control diagrams and operating curves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ReleaseLevel = Literal["normal", "watch", "elevated"]


@dataclass
class ReleaseInputs:
    storage_pct: float | None
    observed_pct_of_normal_precip: float | None  # POWER 30d / climatology, %
    qpf_7d_in: float | None                      # NOAA next-7d total, inches
    snowpack_percentile: float | None            # historical p[0..100] for current month
    forecast_temp_c_avg: float | None            # NOAA next-7d mean 2-m temp
    climatology_temp_c: float | None             # POWER monthly normal


# Thresholds. Tweakable; documented inline so they're easy to reason about.
STORAGE_HIGH = 85.0           # near-capacity → flood-control space starting to matter
STORAGE_WATCH = 75.0
PRECIP_WET_PCT = 130.0        # 30d observed precip ≥ 130% of normal
QPF_WET_INCHES = 1.5          # next-7d ≥ 1.5"
SNOW_HEALTHY_PCTILE = 50.0    # snowpack at or above median ⇒ runoff still ahead
TEMP_WARM_C = 3.0             # 7-day mean ≥ +3°C above normal ⇒ accelerated melt


def evaluate(inputs: ReleaseInputs) -> dict:
    drivers: list[dict] = []

    storage_high = inputs.storage_pct is not None and inputs.storage_pct >= STORAGE_HIGH
    storage_watch = inputs.storage_pct is not None and inputs.storage_pct >= STORAGE_WATCH

    incoming_water = False
    if inputs.observed_pct_of_normal_precip is not None and inputs.observed_pct_of_normal_precip >= PRECIP_WET_PCT:
        incoming_water = True
        drivers.append(
            {
                "key": "wet_observed",
                "label": f"Last 30d precip {inputs.observed_pct_of_normal_precip:.0f}% of normal",
                "weight": "high",
            }
        )
    if inputs.qpf_7d_in is not None and inputs.qpf_7d_in >= QPF_WET_INCHES:
        incoming_water = True
        drivers.append(
            {
                "key": "wet_forecast",
                "label": f"Next 7-day QPF {inputs.qpf_7d_in:.1f} in",
                "weight": "high",
            }
        )

    melt_risk = False
    if inputs.snowpack_percentile is not None and inputs.snowpack_percentile >= SNOW_HEALTHY_PCTILE:
        melt_risk = True
        drivers.append(
            {
                "key": "snow_loaded",
                "label": f"Snowpack at p{inputs.snowpack_percentile:.0f} for this month",
                "weight": "medium",
            }
        )
    if (
        inputs.forecast_temp_c_avg is not None
        and inputs.climatology_temp_c is not None
        and (inputs.forecast_temp_c_avg - inputs.climatology_temp_c) >= TEMP_WARM_C
    ):
        melt_risk = True
        anomaly = inputs.forecast_temp_c_avg - inputs.climatology_temp_c
        drivers.append(
            {
                "key": "warm_forecast",
                "label": f"7-day forecast {anomaly:+.1f}°C vs normal — accelerated melt",
                "weight": "medium",
            }
        )

    if inputs.storage_pct is not None:
        drivers.insert(
            0,
            {
                "key": "storage",
                "label": f"Reservoir at {inputs.storage_pct:.0f}% of capacity",
                "weight": "high" if storage_high else "medium" if storage_watch else "low",
            },
        )

    level: ReleaseLevel = "normal"
    if storage_high and incoming_water and melt_risk:
        level = "elevated"
    elif storage_watch and (incoming_water or melt_risk):
        level = "watch"

    summary = _summary(level, inputs)
    score = _score(level, storage_high, storage_watch, incoming_water, melt_risk)

    return {
        "level": level,
        "score": score,
        "summary": summary,
        "drivers": drivers,
        "thresholds": {
            "storage_high_pct": STORAGE_HIGH,
            "storage_watch_pct": STORAGE_WATCH,
            "precip_wet_pct_of_normal": PRECIP_WET_PCT,
            "qpf_wet_inches": QPF_WET_INCHES,
            "snow_healthy_percentile": SNOW_HEALTHY_PCTILE,
            "temp_warm_anomaly_c": TEMP_WARM_C,
        },
    }


def _score(level: str, storage_high: bool, storage_watch: bool, wet: bool, warm: bool) -> int:
    base = {"normal": 10, "watch": 50, "elevated": 85}[level]
    bump = (5 if storage_high else 0) + (5 if storage_watch else 0) + (5 if wet else 0) + (5 if warm else 0)
    return min(100, base + bump)


def _summary(level: str, inputs: ReleaseInputs) -> str:
    if level == "elevated":
        return (
            "Conditions favor a strategic release: reservoir is near capacity, recent or "
            "forecast precipitation is above normal, and warm or saturated upstream conditions "
            "increase inflow. Watch DWR/USBR notices."
        )
    if level == "watch":
        return (
            "Reservoir is filling and at least one of recent precipitation, forecast rainfall, "
            "or melt risk is above normal. Releases are possible but not yet likely."
        )
    return "Reservoir state and inflow drivers are within normal ranges; no release signal."
