"""GET /api/events — Server-Sent Events stream the dashboard subscribes to.

Used to push notifications when an external caller (the MCP voice agent) runs
a release-estimate query, so the UI can mirror the search.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..events import bus

router = APIRouter()

KEEPALIVE_SECONDS = 25  # browsers/proxies time idle EventSources out at ~30s


@router.get("/events")
async def events_stream(request: Request) -> StreamingResponse:
    async def gen():
        q = bus.subscribe()
        try:
            yield ": ok\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": ka\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
