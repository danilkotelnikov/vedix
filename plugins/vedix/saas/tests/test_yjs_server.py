"""Block 11 Task 1 — Yjs WebSocket reconciliation server.

Spins up a transient instance on a random port, opens two client
connections in the same room (``/doc/test123``), and asserts that a
binary frame sent by one is delivered to the other unchanged.
"""
from __future__ import annotations

import asyncio

import pytest
import websockets

from app.workers.yjs_server import ROOMS, _room_from_path, handler


def test_room_from_path_doc_prefix() -> None:
    assert _room_from_path("/doc/test123") == "test123"


def test_room_from_path_nested_doc_prefix() -> None:
    assert _room_from_path("/doc/palace_abc/branch1") == "palace_abc/branch1"


def test_room_from_path_default() -> None:
    assert _room_from_path("/") == "default"


def test_room_from_path_bare() -> None:
    assert _room_from_path("/abc") == "abc"


async def test_two_clients_sync_text() -> None:
    """A binary frame sent by client A must reach client B in the same room."""
    server = await websockets.serve(handler, "127.0.0.1", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/doc/test123"
        async with websockets.connect(url) as a, websockets.connect(url) as b:
            # Give the server a moment to register both peers in the room.
            await asyncio.sleep(0.05)
            payload = b"\x00\x01\x01\x00"
            await a.send(payload)
            msg = await asyncio.wait_for(b.recv(), timeout=2.0)
            assert msg == payload
    finally:
        server.close()
        await server.wait_closed()


async def test_broadcast_only_to_peers_in_same_room() -> None:
    """A frame sent in room X must NOT be delivered to a peer in room Y."""
    server = await websockets.serve(handler, "127.0.0.1", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        url_x = f"ws://127.0.0.1:{port}/doc/roomX"
        url_y = f"ws://127.0.0.1:{port}/doc/roomY"
        async with websockets.connect(url_x) as ax, websockets.connect(
            url_x
        ) as bx, websockets.connect(url_y) as cy:
            await asyncio.sleep(0.05)
            payload = b"\xff\xee\xdd"
            await ax.send(payload)
            # bx (same room) must get it
            got_bx = await asyncio.wait_for(bx.recv(), timeout=2.0)
            assert got_bx == payload
            # cy (other room) must NOT get it
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(cy.recv(), timeout=0.5)
    finally:
        server.close()
        await server.wait_closed()


async def test_room_cleanup_on_disconnect() -> None:
    """When the last peer leaves a room the entry is reaped from ROOMS."""
    server = await websockets.serve(handler, "127.0.0.1", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/doc/ephemeral"
        async with websockets.connect(url):
            await asyncio.sleep(0.05)
            assert "ephemeral" in ROOMS
        # let the server process the close
        await asyncio.sleep(0.05)
        assert "ephemeral" not in ROOMS
    finally:
        server.close()
        await server.wait_closed()


async def test_sender_does_not_receive_echo() -> None:
    """A peer never receives its own broadcast back."""
    server = await websockets.serve(handler, "127.0.0.1", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/doc/echo_check"
        async with websockets.connect(url) as a, websockets.connect(url) as b:
            await asyncio.sleep(0.05)
            await a.send(b"hello")
            await asyncio.wait_for(b.recv(), timeout=2.0)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(a.recv(), timeout=0.3)
    finally:
        server.close()
        await server.wait_closed()


def test_merge_updates_fallback_without_ypy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without y-py installed the merge function returns a concat fallback."""
    from app.workers import yjs_server

    # Make the y_py import inside merge_updates fail deterministically.
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "y_py":
            raise ImportError("forced for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    merged = yjs_server.merge_updates(b"abc", b"def")
    assert merged == b"abcdef"
