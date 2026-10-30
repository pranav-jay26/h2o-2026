"""Distance-attenuated release-likelihood for a user-supplied location (ZIP or city).

We don't have the river network or Central Valley canal topology, so this is
intentionally a coarse proxy: find the nearest reservoir to the user's centroid
and attenuate that reservoir's release-risk score by distance.

A release from Shasta materially affects the upper Sacramento valley. Beyond
~150 miles the signal is essentially zero for our purposes, so we phase the
factor down linearly to zero at FAR_MILES.
"""

from __future__ import annotations

import math
from typing import Iterable

from ..data_sources.zip_lookup import Resolution

NEAR_MILES = 50.0   # ≤ this: full impact
FAR_MILES = 150.0   # ≥ this: no impact
EARTH_RADIUS_MI = 3958.7613


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def distance_factor(distance_mi: float) -> float:
    if distance_mi <= NEAR_MILES:
        return 1.0
    if distance_mi >= FAR_MILES:
        return 0.0
    return (FAR_MILES - distance_mi) / (FAR_MILES - NEAR_MILES)


def estimate_for_resolution(
    resolution: Resolution,
    reservoirs: Iterable[dict],
) -> dict:
    """`reservoirs` are marker dicts as produced by /api/reservoirs."""
    ranked = []
    for r in reservoirs:
        d = haversine_mi(resolution.lat, resolution.lon, r["lat"], r["lon"])
        ranked.append({"reservoir": r, "distance_mi": round(d, 1), "factor": distance_factor(d)})
    ranked.sort(key=lambda x: x["distance_mi"])

    nearest = ranked[0]
    nearest_res = nearest["reservoir"]
    base_score = float(nearest_res["release_risk"]["score"])
    user_score = round(base_score * nearest["factor"], 1)
    user_level = _level(user_score, nearest["factor"])

    summary = _summary(user_level, nearest_res, nearest["distance_mi"], nearest["factor"])

    return {
        "resolution": {
            "kind": resolution.kind,
            "zip": resolution.zip,
            "city": resolution.city,
            "state_id": resolution.state_id,
            "lat": resolution.lat,
            "lon": resolution.lon,
            "population": resolution.population,
            "matched_zip_count": resolution.matched_zip_count,
        },
        "nearest": {
            "id": nearest_res["id"],
            "name": nearest_res["name"],
            "watershed": nearest_res["watershed"],
            "distance_mi": nearest["distance_mi"],
            "release_level": nearest_res["release_risk"]["level"],
            "release_score": nearest_res["release_risk"]["score"],
            "drivers": nearest_res["release_risk"]["drivers"],
        },
        "user_score": user_score,
        "user_level": user_level,
        "distance_factor": round(nearest["factor"], 2),
        "summary": summary,
        "nearby": [
            {
                "id": r["reservoir"]["id"],
                "name": r["reservoir"]["name"],
                "watershed": r["reservoir"]["watershed"],
                "distance_mi": r["distance_mi"],
                "release_level": r["reservoir"]["release_risk"]["level"],
                "release_score": r["reservoir"]["release_risk"]["score"],
                "factor": round(r["factor"], 2),
            }
            for r in ranked[:3]
        ],
        "thresholds": {
            "near_miles": NEAR_MILES,
            "far_miles": FAR_MILES,
        },
    }


def _level(score: float, factor: float) -> str:
    """User-area level. If they're outside the impact radius, force "out_of_zone"."""
    if factor <= 0:
        return "out_of_zone"
    if score >= 60:
        return "likely"
    if score >= 30:
        return "possible"
    return "unlikely"


def _summary(level: str, reservoir: dict, distance_mi: float, factor: float) -> str:
    name = reservoir["name"]
    if level == "out_of_zone":
        return (
            f"{name} is {distance_mi:.0f} miles away — outside the typical impact range "
            f"for a strategic release. Local conditions are unlikely to be driven by it."
        )
    base = reservoir["release_risk"]["level"]
    factor_pct = int(round(factor * 100))
    if level == "likely":
        return (
            f"{name} (release likelihood: {base}) is {distance_mi:.0f} miles away. "
            f"You're inside the impact zone (~{factor_pct}% attenuation factor) — "
            f"watch for DWR/USBR notices that could affect downstream flows in your area."
        )
    if level == "possible":
        return (
            f"{name} ({base}) is {distance_mi:.0f} miles from your ZIP. Moderate "
            f"chance a release would influence local flows; keep an eye on storm "
            f"and snowmelt updates."
        )
    return (
        f"{name} ({base}) is {distance_mi:.0f} miles away. No strong release signal "
        f"for your area at the moment."
    )
