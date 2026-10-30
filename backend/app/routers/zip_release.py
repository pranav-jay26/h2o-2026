"""GET /api/release-estimate?q=... — distance-attenuated release likelihood
for the user's area, anchored on the nearest tracked reservoir.

Query forms:
- `q=96019`            (5-digit ZIP)
- `q=Sacramento, CA`   (City, ST)
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..analytics.zip_release import estimate_for_resolution
from ..data_sources.zip_lookup import resolve
from .reservoirs import reservoirs as reservoirs_route

router = APIRouter()


@router.get("/release-estimate")
async def release_estimate(q: str) -> dict:
    resolution = resolve(q)
    if resolution is None:
        raise HTTPException(
            404,
            f"Could not resolve '{q}'. Use a 5-digit ZIP or 'City, ST' (e.g. 'Sacramento, CA').",
        )

    # Reuse the /api/reservoirs aggregation so caching + release-risk are identical.
    reservoir_payload = await reservoirs_route()
    estimate = estimate_for_resolution(resolution, reservoir_payload["reservoirs"])

    return {
        "query": q,
        "as_of": datetime.now(timezone.utc).isoformat(),
        **estimate,
    }
