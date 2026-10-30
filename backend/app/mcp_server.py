"""MCP server (JSON-RPC over Streamable HTTP) for ElevenLabs voice agents.

Exposes one tool — `get_release_estimate` — that resolves the caller's location
(5-digit ZIP or "City, ST"), computes the same release-likelihood the dashboard
search bar uses, and publishes the result on the in-process event bus so the UI
mirrors the query in real time.

Mounted on the FastAPI app in `main.py`. The MCP HTTP endpoint lives at
`/mcp/mcp` (FastMCP serves at `/mcp` within its sub-app, mounted under `/mcp`).
ElevenLabs needs a public URL — for local dev, expose port 8000 with ngrok.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .analytics.zip_release import estimate_for_resolution
from .data_sources.zip_lookup import resolve
from .events import bus
from .routers.reservoirs import reservoirs as reservoirs_route

log = logging.getLogger(__name__)

# FastMCP defaults to a localhost-only Host-header allowlist (DNS-rebinding
# protection). We expose this server through cloudflared / ngrok for the
# ElevenLabs voice agent, so we disable that check. For production, set
# enable_dns_rebinding_protection=True and pin allowed_hosts to your tunnel.
_dev_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

mcp = FastMCP(
    name="h2o-water-intel",
    instructions=(
        "Predictive water intelligence for California's Sacramento Valley. "
        "Use `get_release_estimate` to advise a caller on whether a strategic "
        "release from the nearest tracked reservoir is likely to affect their area."
    ),
    transport_security=_dev_security,
)


@mcp.tool()
async def get_release_estimate(query: str) -> dict[str, Any]:
    """Estimate how likely a strategic dam release will affect a caller's area.

    Args:
        query: Either a 5-digit US ZIP code (e.g. "96019") or a city + state in
               the form "City, ST" (e.g. "Sacramento, CA"). The state must be
               the two-letter postal abbreviation.

    Returns:
        A structured assessment containing:
        - resolution: where the query was resolved to (ZIP / city, lat/lon)
        - nearest: name, watershed, distance, current release-likelihood of the
          nearest tracked reservoir (Shasta, Oroville, Trinity, Folsom, or
          New Bullards Bar)
        - user_level: "likely", "possible", "unlikely", or "out_of_zone"
        - user_score: 0–100 distance-attenuated probability score for the area
        - summary: a one-sentence human-readable summary
        - drivers: the inputs that drove the nearest reservoir's status (e.g.,
          storage near capacity, recent precipitation above climatology, warm
          forecast indicating accelerated snowmelt)
    """
    resolution = resolve(query)
    if resolution is None:
        return {
            "error": (
                f"Could not resolve location '{query}'. Ask the caller to "
                f"provide a 5-digit ZIP code or a city + state in the form "
                f"'City, ST' (e.g. 'Sacramento, CA')."
            ),
        }

    payload = await reservoirs_route()
    estimate = estimate_for_resolution(resolution, payload["reservoirs"])
    result = {
        "query": query,
        "as_of": datetime.now(timezone.utc).isoformat(),
        **estimate,
    }

    # Mirror the query on the dashboard via SSE so the UI shows the same tile
    # it would render if the caller had typed into the search box.
    try:
        await bus.publish(
            {"type": "release_estimate", "query": query, "result": result}
        )
    except Exception as e:  # never let the UI bridge fail the tool call
        log.warning("event publish failed: %s", e)

    return result
