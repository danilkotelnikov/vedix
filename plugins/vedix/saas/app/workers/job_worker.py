"""arq-based worker that picks queued jobs and runs the orchestrator.

The worker loads the persisted ``Job`` row, marks it ``running``,
instantiates a fresh ``Pipeline`` against a per-job workspace, and
delegates to ``pipeline.run_full_pipeline``. On success the row is
flipped to ``done`` with ``artifact_root`` populated; on failure the
exception message lands on ``Job.error`` and the row goes to
``failed``. The orchestrator import is lazy so partial-checkout
contexts (e.g. unit tests for the FastAPI plumbing) don't drag the
whole plugin tree onto sys.path.
"""
from __future__ import annotations

import asyncio
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select

from .. import db as db_mod
from ..config import settings
from ..models.job import Job


# ---------- orchestrator lazy import -------------------------------


def _load_pipeline_class() -> Any:
    """Add ``plugins/vedix/mcp/lib`` to ``sys.path`` and import Pipeline."""
    saas_root = Path(__file__).resolve().parents[2]
    lib_path = saas_root.parent / "mcp" / "lib"
    if lib_path.exists() and str(lib_path) not in sys.path:
        sys.path.insert(0, str(lib_path))
    from orchestrator.pipeline import Pipeline  # type: ignore[import]

    return Pipeline


# ---------- job state helpers --------------------------------------


async def _mark_running(job_id: uuid.UUID) -> Job:
    async with db_mod.SessionLocal() as db:
        job = (
            await db.execute(select(Job).where(Job.id == job_id))
        ).scalar_one()
        job.state = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(job)
        return job


async def _mark_done(job_id: uuid.UUID, artifact_root: str) -> None:
    async with db_mod.SessionLocal() as db:
        job = (
            await db.execute(select(Job).where(Job.id == job_id))
        ).scalar_one()
        job.state = "done"
        job.finished_at = datetime.now(timezone.utc)
        job.artifact_root = artifact_root
        job.progress = 100
        await db.commit()


async def _mark_failed(job_id: uuid.UUID, error: str) -> None:
    async with db_mod.SessionLocal() as db:
        job = (
            await db.execute(select(Job).where(Job.id == job_id))
        ).scalar_one()
        job.state = "failed"
        job.finished_at = datetime.now(timezone.utc)
        job.error = error[:2000]
        await db.commit()


def _job_workspace(job_id: uuid.UUID) -> Path:
    root = Path(settings.job_workspace_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    ws = root / str(job_id)
    ws.mkdir(parents=True, exist_ok=True)
    return ws


# ---------- the worker function -----------------------------------


async def run_job(ctx: dict[str, Any], job_id_str: str) -> dict[str, Any]:
    """arq entrypoint — load the Job, run the orchestrator, persist outcome."""
    job_id = uuid.UUID(job_id_str)
    job = await _mark_running(job_id)
    workspace = _job_workspace(job_id)
    try:
        Pipeline = _load_pipeline_class()
        pipeline = Pipeline(
            workspace=workspace,
            language=job.setup.get("language", "en"),
            project_id=str(job_id),
        )
        topic = job.setup["topic"]
        domain = job.setup.get("discipline", "chemistry")
        codebase = job.setup.get("codebase_path")
        # ``run_full_pipeline`` is sync — push it onto a worker thread so
        # we don't block the asyncio loop.
        result = await asyncio.to_thread(
            pipeline.run_full_pipeline,
            topic=topic,
            domain=domain,
            output_dir=workspace,
            codebase_path=Path(codebase) if codebase else None,
        )
        await _mark_done(job_id, artifact_root=str(workspace))
        return {"status": "ok", "job_id": str(job_id), "result": result}
    except Exception as exc:
        tb = traceback.format_exc()
        await _mark_failed(job_id, error=f"{exc}\n\n{tb}")
        # Re-raise so arq logs the failure and respects retry policy.
        raise


# ---------- WorkerSettings + enqueue helper ------------------------


class WorkerSettings:
    functions = [run_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 60 * 60 * 4  # cap at 4h — Lab tier ceiling


async def enqueue_job(job_id: uuid.UUID) -> None:
    """Push the job onto the Redis queue. Best-effort; failures are
    swallowed by the caller so the API still returns 201."""
    pool = await create_pool(WorkerSettings.redis_settings)
    try:
        await pool.enqueue_job("run_job", str(job_id))
    finally:
        await pool.close()


__all__ = [
    "WorkerSettings",
    "enqueue_job",
    "run_job",
]
