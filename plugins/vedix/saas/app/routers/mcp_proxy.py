"""``/v1/api/mcp`` — per-user MCP proxy with per-tier rate limits.

Sliding-window counter (1-minute buckets) lives in Redis under
``rl:<user>:<mcp>:<bucket>`` keys. Free tier is capped at 30/min, Solo
at 120, Lab at 600; Institution defers to its contract (no cap here).
The actual subprocess fan-out happens via the ``MCPPool`` in
``workers.mcp_pool``.
"""
from __future__ import annotations

import time
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth_utils import get_current_user
from ..config import settings
from .. import db as db_mod
from ..entitlements import compute_entitlements
from ..models.user import User
from ..workers.mcp_pool import MCP_COMMANDS, MCPPool, get_pool

router = APIRouter(prefix="/v1/api/mcp", tags=["mcp"])


_redis_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url)
    return _redis_client


def reset_redis_client() -> None:
    """Test helper — invalidates the cached client so a fresh fakeredis can land."""
    global _redis_client
    _redis_client = None


async def _rate_limit(user_id: str, mcp_name: str, per_min: int) -> tuple[bool, int]:
    """Increment the current 1-minute bucket; return (allowed, current count)."""
    bucket = int(time.time() // 60)
    key = f"rl:{user_id}:{mcp_name}:{bucket}"
    client = _redis()
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, 60)
    return count <= per_min, int(count)


async def _resolve_tier(user: User) -> str:
    """Resolve the user's active subscription tier without leaking a session."""
    from .jobs import _user_subscription_tier  # local import avoids cycle

    # Look up SessionLocal lazily so test fixtures that rebind it on
    # ``app.db`` take effect.
    async with db_mod.SessionLocal() as db:
        tier = await _user_subscription_tier(user, db)
    return tier.value


@router.get("/list")
async def list_mcps(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """List the MCP fleet the calling user has access to (= all)."""
    return {"mcps": sorted(MCP_COMMANDS.keys()), "available_to": "all-tiers"}


@router.post("/{mcp_name}/call")
async def call_mcp(
    mcp_name: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if mcp_name not in MCP_COMMANDS:
        raise HTTPException(status_code=404, detail=f"unknown MCP: {mcp_name}")

    tier_value = await _resolve_tier(user)
    from ..entitlements import Tier  # local import

    ent = compute_entitlements(tier=Tier(tier_value))
    per_min_raw = ent["mcp_rate_limit_per_min"]
    per_min = per_min_raw if isinstance(per_min_raw, int) else 10_000

    allowed, count = await _rate_limit(str(user.id), mcp_name, per_min)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"MCP rate limit {per_min}/min exceeded for {tier_value} "
                f"(current {count})"
            ),
        )

    body = await request.json()
    pool: MCPPool = get_pool()
    return await pool.call(mcp_name, body)


__all__ = ["router", "reset_redis_client"]
