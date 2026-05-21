"""§5.7 SSE event emitter for the web UI (Block 9).

The orchestrator broadcasts every pipeline phase change, every artifact
write, every agent dispatch, and every cost / token update through this
event bus. The web UI subscribes to `/events?since_id=N` and renders the
stream as a live activity feed.

We keep a bounded in-memory ring buffer (default 10 000 events). Late
subscribers replay missed events by passing `since_id`. The bus is
process-local — distributed fan-out (Redis pub/sub etc.) is Block 9's
concern and not needed for the orchestrator-side hook.
"""
from __future__ import annotations

import json
import time
from collections import deque
from typing import Any, Iterator


class EventBus:
    """Ring-buffered SSE event broadcaster."""

    def __init__(self, max_buffer: int = 10_000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_buffer)
        self._next_id = 0

    def emit(self, *, kind: str, payload: dict[str, Any]) -> int:
        """Append an event and return its monotonic id."""
        event: dict[str, Any] = {
            "id": self._next_id,
            "ts": time.time(),
            "kind": kind,
            "payload": payload,
        }
        self._events.append(event)
        self._next_id += 1
        return int(event["id"])

    def stream(self, *, since_id: int = 0) -> Iterator[str]:
        """Yield SSE-framed events with `id > since_id`."""
        for e in self._events:
            if e["id"] > since_id:
                yield (
                    f"id: {e['id']}\n"
                    f"event: {e['kind']}\n"
                    f"data: {json.dumps(e['payload'])}\n\n"
                )


_BUS = EventBus()


def emit(kind: str, payload: dict[str, Any]) -> int:
    """Module-level wrapper around the singleton `EventBus.emit`."""
    return _BUS.emit(kind=kind, payload=payload)


def stream(since_id: int = 0) -> Iterator[str]:
    """Module-level wrapper around the singleton `EventBus.stream`."""
    return _BUS.stream(since_id=since_id)
