"""B12 §5 — end-to-end pipeline smoke against a live Vedix.ai SaaS.

The test submits the smallest meaningful pipeline job (a synthetic linear
correlation experiment), polls until the SaaS reports a terminal state, and
asserts the final state is ``done``.

Skips cleanly when ``VEDIX_SAAS_TOKEN`` is unset so the test stays runnable
in unit-test CI without leaking secrets or requiring a deployed SaaS.
"""
from __future__ import annotations

import time

import pytest

# httpx is the project's HTTP client (already pinned in plugin requirements).
# Import via importorskip so the smoke module loads even on a slim test env.
httpx = pytest.importorskip("httpx")


_TERMINAL_STATES = frozenset({"done", "failed", "cancelled"})

# Polling parameters: up to 60 iterations * 30 s = 30 min max wall time, which
# matches the spec's nominal pipeline upper bound for a synthetic job.
_MAX_POLLS = 60
_POLL_INTERVAL_S = 30


@pytest.mark.smoke
def test_full_pipeline_e2e(saas_url: str, saas_token: str) -> None:
    """Submit a tiny job and wait until the SaaS marks it ``done``."""
    if not saas_token:
        pytest.skip(
            "VEDIX_SAAS_TOKEN not set; cannot run live SaaS smoke. "
            "Set the env var or pass --smoke-saas-token=… to enable."
        )

    headers = {
        "Authorization": f"Bearer {saas_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "topic": (
            "Detecting if x correlates with y in synthetic linear data"
        ),
        "discipline": "computer_science",
        "language": "en",
        "venue": "preprint",
        "hypothesis_style": "exploratory",
        "experiment_type": "computational",
        "primary_metric": "pearson_r",
        "expected_direction": "increase",
        "tolerance": 0.05,
    }

    with httpx.Client(timeout=60.0) as client:
        # 1. Submit the job.
        submit = client.post(
            f"{saas_url}/v1/api/jobs",
            json=payload,
            headers=headers,
        )
        assert submit.status_code == 201, (
            f"job submit returned {submit.status_code}: {submit.text}"
        )
        body = submit.json()
        job_id = body["job_id"]
        assert isinstance(job_id, str) and job_id, "missing job_id in response"

        # 2. Poll for terminal state.
        status: dict[str, object] = {"state": "queued"}
        for _ in range(_MAX_POLLS):
            poll = client.get(
                f"{saas_url}/v1/api/jobs/{job_id}",
                headers=headers,
            )
            assert poll.status_code == 200, (
                f"status poll returned {poll.status_code}: {poll.text}"
            )
            status = poll.json()
            if status.get("state") in _TERMINAL_STATES:
                break
            time.sleep(_POLL_INTERVAL_S)

        # 3. Assert the terminal state is success.
        assert status.get("state") == "done", (
            f"job {job_id} ended in non-success state: {status!r}"
        )


@pytest.mark.smoke
def test_health_check(saas_url: str, saas_token: str) -> None:
    """Lightweight live-SaaS reachability check.

    Hits the unauthenticated health endpoint to confirm the SaaS is reachable
    before the longer end-to-end pipeline test attempts to use it. Also skips
    when no token is configured so it pairs naturally with the e2e test.
    """
    if not saas_token:
        pytest.skip("VEDIX_SAAS_TOKEN not set; cannot run live SaaS smoke.")

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{saas_url}/healthz")
        assert resp.status_code == 200, (
            f"healthz returned {resp.status_code}: {resp.text}"
        )
