"""§§5.10/5.11 Y.js-compatible WebSocket reconciliation server.

Each WebSocket connection joins a *room* identified by the trailing
segment of the request path (URL convention: ``/doc/{doc_id}``). Every
binary frame received on a connection is broadcast to every other
connection in the same room, which is exactly the wire-level contract
the ``y-websocket`` reference implementation in JavaScript expects.

This module deliberately stays protocol-agnostic about Yjs payloads —
the server only ferries opaque binary blobs. Yjs reconciliation
happens inside the clients (the browser uses ``yjs`` + ``y-websocket``;
Python clients can use ``y-py``). When ``y-py`` is installed the server
can optionally hydrate / persist Yjs state via :func:`apply_update` and
:func:`encode_state_as_update`, but the broadcast path itself does not
depend on it.

Compatibility:

* ``websockets`` >= 12 ships the legacy ``WebSocketServerProtocol`` whose
  handler receives ``(ws, path)``.
* ``websockets`` >= 13 (and definitely 16+) ships the new
  ``asyncio.server.ServerConnection`` whose handler receives ``(conn,)``
  alone and exposes the request line via ``conn.request.path``.

:func:`handler` accepts both shapes — it inspects ``*args`` to figure
out which API surface invoked it and resolves the path accordingly.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

import websockets

log = logging.getLogger(__name__)

# room_id -> set of live connections
ROOMS: dict[str, set[Any]] = defaultdict(set)
# per-room lock, used to keep add/discard atomic against the broadcast loop
ROOM_LOCKS: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _extract_path(ws: Any, fallback: str | None) -> str:
    """Resolve the request path across websockets 12.x and 13+ APIs."""
    if fallback is not None:
        return fallback
    # websockets >= 13: handler signature is (conn,) and the request is
    # available on the connection object.
    req = getattr(ws, "request", None)
    if req is not None and getattr(req, "path", None):
        return req.path
    # last-ditch: some forks expose .path directly
    return getattr(ws, "path", "") or ""


def _room_from_path(path: str) -> str:
    """``/doc/abc/xyz`` → ``abc/xyz``; bare ``/`` → ``default``."""
    stripped = path.strip("/")
    if not stripped:
        return "default"
    if "/" not in stripped:
        # ``/abc`` → treat as room id
        return stripped
    head, _, tail = stripped.partition("/")
    if head == "doc":
        return tail or "default"
    return stripped


async def handler(ws: Any, path: str | None = None) -> None:
    """Broadcast every received frame to every other peer in the same room.

    Works against both the legacy ``(ws, path)`` and the modern
    ``(conn,)`` handler signatures.
    """
    resolved_path = _extract_path(ws, path)
    room = _room_from_path(resolved_path)
    async with ROOM_LOCKS[room]:
        ROOMS[room].add(ws)
    log.info("client joined room=%s size=%d", room, len(ROOMS[room]))
    try:
        async for msg in ws:
            peers = [p for p in ROOMS[room] if p is not ws]
            if not peers:
                continue
            await asyncio.gather(
                *(p.send(msg) for p in peers),
                return_exceptions=True,
            )
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("handler exception room=%s: %r", room, exc)
    finally:
        async with ROOM_LOCKS[room]:
            ROOMS[room].discard(ws)
            if not ROOMS[room]:
                del ROOMS[room]
            log.info("client left room=%s", room)


# ---------------------------------------------------------------------------
# Optional Yjs state hydration (requires y-py).
# Used by the snapshot persistence model (yjs_doc.YjsDoc) when the worker
# wants to roll a fresh state vector into Postgres or rehydrate a doc on
# server restart. Importing y-py lazily keeps the broadcast hot path free
# of native dependencies on stripped-down deployments.
# ---------------------------------------------------------------------------
def merge_updates(existing: bytes, incoming: bytes) -> bytes:
    """Fold ``incoming`` into ``existing`` and return the new state vector.

    Falls back to a pure-Python length-prefix concat (the resulting blob
    is *not* a valid Yjs update — only the binary length is meaningful)
    when ``y-py`` is unavailable. Callers should treat the fallback as a
    durable opaque snapshot for restart, not as a Yjs encode.
    """
    try:
        import y_py  # type: ignore[import-not-found]
    except ImportError:
        return existing + incoming
    doc = y_py.YDoc()
    if existing:
        y_py.apply_update(doc, existing)
    if incoming:
        y_py.apply_update(doc, incoming)
    return y_py.encode_state_as_update(doc)


async def main(host: str = "0.0.0.0", port: int = 1234) -> None:
    """Run the Yjs WS server forever."""
    # Use the legacy ``websockets.serve`` for broadest compatibility.
    async with websockets.serve(handler, host, port):
        log.info("Yjs WS server listening on %s:%d", host, port)
        await asyncio.Future()  # block forever


if __name__ == "__main__":  # pragma: no cover - manual run
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
