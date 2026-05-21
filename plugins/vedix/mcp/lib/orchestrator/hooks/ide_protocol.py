"""§5.8 IDE-plugin JSON-RPC protocol.

VS Code (B10a) and JetBrains (B10b) plugins both speak JSON-RPC 2.0 to the
orchestrator. This module declares the seven methods the plugins are
expected to call. Each method's full handler lands in Block 10; the
stub here is enough for the dispatcher / router to validate method
names today.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IDERequest:
    """A JSON-RPC 2.0 request from the IDE plugin."""

    method: str
    params: dict[str, Any]
    id: int


@dataclass
class IDEResponse:
    """A JSON-RPC 2.0 response back to the IDE plugin."""

    result: dict[str, Any] | None
    error: dict[str, Any] | None
    id: int


# Method-name → human description. Block 10 fills in real handlers.
SUPPORTED_METHODS: dict[str, str] = {
    "job.new": "params: ExperimentSetup -> job_id",
    "job.status": "params: {job_id} -> {phase, progress, partial_artifacts}",
    "job.cancel": "params: {job_id} -> {ok}",
    "provider.list": "params: {} -> [{name, region, model}]",
    "cost.report": "params: {since_iso} -> {total_usd, per_provider}",
    "manuscript.preview": "params: {job_id} -> {pdf_url, latex_path}",
    "rationale.fetch": "params: {artifact_path} -> markdown",
}


def handle(req: IDERequest) -> IDEResponse:
    """Stub handler. Returns an echo response for known methods, a
    JSON-RPC `method not found` error otherwise.
    """
    if req.method not in SUPPORTED_METHODS:
        return IDEResponse(
            result=None,
            error={
                "code": -32601,
                "message": f"method {req.method} not supported",
            },
            id=req.id,
        )
    return IDEResponse(
        result={"stub": True, "method": req.method, "params": req.params},
        error=None,
        id=req.id,
    )
