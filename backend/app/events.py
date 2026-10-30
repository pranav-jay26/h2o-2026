"""In-process pub/sub for pushing events from server-side handlers (the MCP
tool) to active SSE subscribers (the dashboard).

Single-process only — no Redis or message broker. Each subscriber gets its own
`asyncio.Queue` and reads it inside the SSE generator.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)


class EventBus:
    def __init__(self, max_queue: int = 32) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._max_queue = max_queue

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._max_queue)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                log.warning("dropping event for slow subscriber")

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


bus = EventBus()
