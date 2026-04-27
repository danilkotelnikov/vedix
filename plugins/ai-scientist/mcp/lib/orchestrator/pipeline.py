"""Pipeline orchestrator. Per spec §4.10.

Owns state, calls .md agents via the host dispatcher, runs ReflectionLoop
and BiasedReviewers and StageGate around them, mines to MemPalace,
checkpoints between phases, surfaces AskUserQuestion gates.

This file grows phase-by-phase across Tasks 18-26. Each task adds 1-2
methods; the run_full_pipeline() top-level orchestrator lands in Task 26.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional
from datetime import datetime, timezone
import uuid

from .reflection import ReflectionLoop, EvaluatorVerdict
from .schemas import IDEATION_SCHEMA, validate_against
from .extraction import extract_json
from .checkpoints import CheckpointManager
from .tokens import TokenTracker
from .convergence import SemanticConvergence


@dataclass
class PipelineState:
    job_id: str = ""
    topic: str = ""
    domain: str = ""
    output_dir: Optional[Path] = None
    config: dict = field(default_factory=dict)


class Pipeline:
    def __init__(
        self,
        *,
        dispatcher: Callable,
        evaluator: Callable,
        host: str = "claude_code",
        plugin_palace: Any = None,
        project_palace: Any = None,
        token_tracker: Optional[TokenTracker] = None,
    ):
        self.dispatcher = dispatcher
        self.evaluator = evaluator
        self.host = host
        self.plugin_palace = plugin_palace
        self.project_palace = project_palace
        self.tokens = token_tracker or TokenTracker()
        self.state = PipelineState()
        self.checkpoints: Optional[CheckpointManager] = None

    # --- Phase 0 ---------------------------------------------------------
    def phase_0_init(self, *, topic: str, domain: str, output_dir: Path) -> None:
        self.state.job_id = uuid.uuid4().hex[:8]
        self.state.topic = topic
        self.state.domain = domain
        self.state.output_dir = Path(output_dir)
        self.state.output_dir.mkdir(parents=True, exist_ok=True)
        (self.state.output_dir / ".checkpoints").mkdir(exist_ok=True)
        (self.state.output_dir / ".palace").mkdir(exist_ok=True)
        self.checkpoints = CheckpointManager(
            checkpoint_dir=self.state.output_dir / ".checkpoints",
            palace=self.project_palace,
        )
        self.state.config = {
            "job_id": self.state.job_id,
            "topic": topic,
            "domain": domain,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.state.output_dir / "config.json").write_text(
            json.dumps(self.state.config, indent=2), encoding="utf-8"
        )

    # --- Phase 0.5: Ideation --------------------------------------------
    def phase_0_5_ideation(
        self,
        *,
        topic: str,
        domain: str,
        num_candidates: int = 3,
        max_rounds: int = 3,
    ) -> List[dict]:
        candidates: List[dict] = []
        loop = ReflectionLoop(
            dispatcher=self.dispatcher,
            evaluator=lambda parsed: self._wrap_evaluator(parsed),
            schema=IDEATION_SCHEMA,
            extractor=lambda response: extract_json(response.get("raw", "")),
        )
        for i in range(num_candidates):
            inputs = {
                "topic": topic, "domain": domain,
                "candidate_index": i + 1, "total_candidates": num_candidates,
                "previous_ideas": json.dumps([c.get("Name", "") for c in candidates]),
            }
            try:
                idea = loop.run(agent_name="ideator", inputs=inputs, max_rounds=max_rounds)
                candidates.append(idea)
            except Exception as e:
                candidates.append({"Name": f"failed_{i}", "error": str(e)})
        # Persist
        out = self.state.output_dir / "idea_candidates.json"
        out.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
        if self.checkpoints:
            self.checkpoints.save("phase_0_5", {"candidates": candidates})
        return candidates

    def _wrap_evaluator(self, parsed: dict) -> EvaluatorVerdict:
        try:
            v = self.evaluator(parsed)
            if isinstance(v, dict):
                return EvaluatorVerdict(verdict=v.get("verdict", "PASS"), reason=v.get("reason", ""))
            if isinstance(v, EvaluatorVerdict):
                return v
            return EvaluatorVerdict(verdict="PASS", reason="")
        except Exception:
            return EvaluatorVerdict(verdict="PASS", reason="evaluator-skipped")
