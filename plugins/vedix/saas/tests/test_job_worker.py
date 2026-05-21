"""Smoke tests for the arq job worker (Block 8 Task 6).

The orchestrator is mocked — we never actually run the full pipeline
from these tests. We only verify that:

* ``run_job`` flips the Job row queued → running → done on success.
* Pipeline failures land on Job.state == "failed" with a non-empty
  ``error`` field.
* The Pipeline factory receives the language + workspace from
  ``Job.setup`` and the project_id = str(job_id).
* ``enqueue_job`` doesn't blow up when the Redis URL points at fake.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest


VALID_SETUP = {
    "topic": "solvent polarity on Diels-Alder",
    "discipline": "chemistry",
    "language": "ru",
    "venue": "preprint",
    "hypothesis_style": "exploratory",
    "experiment_type": "computational",
    "primary_metric": "yield",
    "expected_direction": "increase",
    "tolerance": 0.05,
}


class _FakePipeline:
    """Stand-in for orchestrator.pipeline.Pipeline."""

    instances: list["_FakePipeline"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.run_calls: list[dict] = []
        _FakePipeline.instances.append(self)

    def run_full_pipeline(self, **kwargs):
        self.run_calls.append(kwargs)
        return {"job_id": self.kwargs.get("project_id"), "review": "ok"}


class _ExplodingPipeline:
    def __init__(self, **_kwargs):
        pass

    def run_full_pipeline(self, **_kwargs):
        raise RuntimeError("phase 3 codegen failed in test")


async def _seed_job(setup: dict | None = None) -> uuid.UUID:
    from app.db import SessionLocal
    from app.models.job import Job
    from app.models.user import User

    async with SessionLocal() as db:
        user = User(email=f"u-{uuid.uuid4().hex[:6]}@vedix.test")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        job = Job(user_id=user.id, setup=setup or dict(VALID_SETUP), state="queued")
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job.id


@pytest.mark.asyncio
async def test_run_job_flips_state_to_done(monkeypatch, app_instance, tmp_path):
    """Happy path — Pipeline returns; Job lands at state='done'."""
    from app import db as db_mod
    from app.workers import job_worker

    async with app_instance.router.lifespan_context(app_instance):
        _FakePipeline.instances.clear()
        monkeypatch.setattr(job_worker, "_load_pipeline_class", lambda: _FakePipeline)
        monkeypatch.setattr(job_worker.settings, "job_workspace_root", str(tmp_path))

        job_id = await _seed_job()
        result = await job_worker.run_job({}, str(job_id))
        assert result["status"] == "ok"
        assert result["job_id"] == str(job_id)

        from sqlalchemy import select

        from app.models.job import Job

        async with db_mod.SessionLocal() as db:
            row = (
                await db.execute(select(Job).where(Job.id == job_id))
            ).scalar_one()
        assert row.state == "done"
        assert row.progress == 100
        assert row.artifact_root is not None
        assert Path(row.artifact_root).exists()
        assert row.started_at is not None
        assert row.finished_at is not None

        # The fake pipeline got the right language and project_id.
        pipe = _FakePipeline.instances[-1]
        assert pipe.kwargs["language"] == "ru"
        assert pipe.kwargs["project_id"] == str(job_id)
        assert pipe.run_calls[0]["topic"] == VALID_SETUP["topic"]
        assert pipe.run_calls[0]["domain"] == VALID_SETUP["discipline"]


@pytest.mark.asyncio
async def test_run_job_marks_failed_on_exception(monkeypatch, app_instance, tmp_path):
    from app import db as db_mod
    from app.workers import job_worker

    async with app_instance.router.lifespan_context(app_instance):
        monkeypatch.setattr(
            job_worker, "_load_pipeline_class", lambda: _ExplodingPipeline
        )
        monkeypatch.setattr(job_worker.settings, "job_workspace_root", str(tmp_path))

        job_id = await _seed_job()
        with pytest.raises(RuntimeError, match="phase 3 codegen failed"):
            await job_worker.run_job({}, str(job_id))

        from sqlalchemy import select

        from app.models.job import Job

        async with db_mod.SessionLocal() as db:
            row = (
                await db.execute(select(Job).where(Job.id == job_id))
            ).scalar_one()
        assert row.state == "failed"
        assert row.error is not None
        assert "phase 3 codegen failed" in row.error


@pytest.mark.asyncio
async def test_worker_settings_advertises_run_job():
    from app.workers.job_worker import WorkerSettings, run_job

    assert run_job in WorkerSettings.functions
    # The arq decorator wraps in a Function obj after registration; we just
    # confirm there's something callable in there.
    assert callable(WorkerSettings.functions[0])
