"""Tests for the hosted MCP proxy (Block 8 Task 4).

Verifies:

* GET /list returns all 9 hosted MCPs.
* POST /{name}/call dispatches to the (test-injected) MCPPool.
* Free-tier rate limit (30/min) returns 429 on the 31st call.
* Solo-tier (120/min) lets a Free-tier-blocked call through.
* Unknown MCP name returns 404.
* MCPPool roundtrip works against a fake subprocess (line-delimited JSON).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import pytest

VALID_RPC = {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}


class DummyPool:
    """In-process pool — records calls, returns scripted responses."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call(self, name: str, body: dict) -> dict:
        self.calls.append((name, body))
        return {"ok": True, "mcp": name, "echo": body}


async def _create_user(*, tier=None):
    from app.auth_utils import issue_jwt
    from app.db import SessionLocal
    from app.models.subscription import Subscription
    from app.models.user import User

    async with SessionLocal() as db:
        user = User(email=f"u-{uuid.uuid4().hex[:6]}@vedix.test")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        if tier is not None:
            sub = Subscription(
                user_id=user.id,
                tier=tier.value if hasattr(tier, "value") else tier,
                status="active",
                payment_provider="stripe",
            )
            db.add(sub)
            await db.commit()
        return {
            "id": user.id,
            "email": user.email,
            "token": issue_jwt(user_id=str(user.id), email=user.email),
        }


@pytest.fixture
def dummy_pool(monkeypatch):
    from app.routers import mcp_proxy
    from app.workers import mcp_pool

    pool = DummyPool()
    monkeypatch.setattr(mcp_pool, "_GLOBAL_POOL", pool)
    monkeypatch.setattr(mcp_pool, "get_pool", lambda: pool)
    monkeypatch.setattr(mcp_proxy, "get_pool", lambda: pool)
    # Invalidate any cached redis client so the autouse fake lands.
    mcp_proxy.reset_redis_client()
    return pool


@pytest.mark.asyncio
async def test_list_returns_all_nine_mcps(app_instance, dummy_pool):  # noqa: ARG001
    from httpx import ASGITransport, AsyncClient

    async with app_instance.router.lifespan_context(app_instance):
        u = await _create_user()
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {u['token']}"},
        ) as ac:
            r = await ac.get("/v1/api/mcp/list")
            assert r.status_code == 200
            data = r.json()
            assert data["available_to"] == "all-tiers"
            assert set(data["mcps"]) == {
                "vedix",
                "mempalace",
                "openalex",
                "semanticscholar",
                "arxiv",
                "biorxiv",
                "pubmed",
                "annas-mcp",
                "fetcher",
            }


@pytest.mark.asyncio
async def test_call_dispatches_to_pool(app_instance, dummy_pool):
    from httpx import ASGITransport, AsyncClient

    async with app_instance.router.lifespan_context(app_instance):
        u = await _create_user()
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {u['token']}"},
        ) as ac:
            r = await ac.post("/v1/api/mcp/openalex/call", json=VALID_RPC)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["ok"] is True
            assert body["mcp"] == "openalex"
            assert dummy_pool.calls == [("openalex", VALID_RPC)]


@pytest.mark.asyncio
async def test_unknown_mcp_returns_404(app_instance, dummy_pool):  # noqa: ARG001
    from httpx import ASGITransport, AsyncClient

    async with app_instance.router.lifespan_context(app_instance):
        u = await _create_user()
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {u['token']}"},
        ) as ac:
            r = await ac.post("/v1/api/mcp/foo/call", json=VALID_RPC)
            assert r.status_code == 404


@pytest.mark.asyncio
async def test_free_tier_rate_limit_30_per_min(app_instance, dummy_pool):  # noqa: ARG001
    from httpx import ASGITransport, AsyncClient

    async with app_instance.router.lifespan_context(app_instance):
        u = await _create_user()  # default FREE
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {u['token']}"},
        ) as ac:
            for i in range(30):
                r = await ac.post("/v1/api/mcp/arxiv/call", json=VALID_RPC)
                assert r.status_code == 200, f"call #{i+1} should pass"
            r = await ac.post("/v1/api/mcp/arxiv/call", json=VALID_RPC)
            assert r.status_code == 429
            assert "30/min" in r.json()["detail"]
            assert "free" in r.json()["detail"]


@pytest.mark.asyncio
async def test_solo_tier_higher_rate_limit(app_instance, dummy_pool):  # noqa: ARG001
    from app.entitlements import Tier
    from httpx import ASGITransport, AsyncClient

    async with app_instance.router.lifespan_context(app_instance):
        u = await _create_user(tier=Tier.SOLO)
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {u['token']}"},
        ) as ac:
            # Solo = 120/min. The 31st request (which would have 429'd on
            # Free) must succeed here.
            for i in range(50):
                r = await ac.post("/v1/api/mcp/pubmed/call", json=VALID_RPC)
                assert r.status_code == 200, f"solo call #{i+1} should pass"


@pytest.mark.asyncio
async def test_institution_tier_uncapped(app_instance, dummy_pool):  # noqa: ARG001
    from app.entitlements import Tier
    from httpx import ASGITransport, AsyncClient

    async with app_instance.router.lifespan_context(app_instance):
        u = await _create_user(tier=Tier.INSTITUTION)
        async with AsyncClient(
            transport=ASGITransport(app=app_instance),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {u['token']}"},
        ) as ac:
            # Institution = per-contract → no in-app cap → 10_000 ceiling.
            # We send well below the ceiling but well above Free/Solo caps.
            for _ in range(200):
                r = await ac.post("/v1/api/mcp/openalex/call", json=VALID_RPC)
                assert r.status_code == 200


# -------------- MCPPool unit tests against a fake subprocess --------


class _FakeStream:
    def __init__(self) -> None:
        self.buffer: list[bytes] = []
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()

    def write(self, data: bytes) -> None:
        self.buffer.append(data)

    async def drain(self) -> None:
        return None

    async def readline(self) -> bytes:
        return await self.queue.get()


class _FakeProc:
    def __init__(self) -> None:
        self.stdin = _FakeStream()
        self.stdout = _FakeStream()
        self.stderr = _FakeStream()

    def terminate(self) -> None:
        return None

    async def wait(self) -> int:
        return 0


@pytest.mark.asyncio
async def test_mcp_pool_roundtrips_json(monkeypatch):
    from app.workers import mcp_pool

    fake = _FakeProc()

    async def _spawn(*_args: Any, **_kwargs: Any) -> _FakeProc:
        return fake

    monkeypatch.setattr(
        mcp_pool.asyncio, "create_subprocess_exec", _spawn  # type: ignore[attr-defined]
    )

    # Pre-stage a response.
    await fake.stdout.queue.put((json.dumps({"ok": True}) + "\n").encode("utf-8"))

    pool = mcp_pool.MCPPool()
    resp = await pool.call("openalex", {"method": "search", "params": {"q": "x"}})
    assert resp == {"ok": True}
    written = b"".join(fake.stdin.buffer).decode("utf-8")
    assert json.loads(written.strip())["method"] == "search"
    await pool.shutdown()


@pytest.mark.asyncio
async def test_mcp_pool_unknown_name_raises(monkeypatch):
    from app.workers import mcp_pool

    pool = mcp_pool.MCPPool()
    with pytest.raises(KeyError):
        await pool.ensure("definitely-not-an-mcp")
