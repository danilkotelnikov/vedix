"""Build reviewer_dispatch.json artifact (closes review-doc finding #11)."""
from __future__ import annotations
from typing import Optional


def build_reviewer_dispatch(reviewers: list, *, mode: str,
                            max_threads: int,
                            fallback_reason: Optional[str]) -> dict:
    """Returns dict matching REVIEWER_DISPATCH_SCHEMA."""
    return {
        "mode": mode,
        "max_threads": max_threads,
        "reviewers": [
            {
                "role": r.get("role", ""),
                "agent_id": r.get("agent_id"),
                "agent_type": r.get("agent_type"),
                "model": r.get("model"),
                "status": r.get("status", "completed"),
            } for r in reviewers
        ],
        "fallback_reason": fallback_reason,
    }


# --- v3.0.0 Block 13: SGCA reviewer-KG namespace allocation ---------------
def reviewer_kg_scope_id(*, reviewer_id: str, job_id: str) -> str:
    """Match the wing naming convention in SGCA §6.1.
    Returns the scope_id used to open a KGStore(tier=REVIEWER, scope_id=...).
    """
    return f"{reviewer_id}__{job_id}"
