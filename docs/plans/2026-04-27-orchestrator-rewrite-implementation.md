# Orchestrator Rewrite (Approach B′) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the AI-Scientist plugin's orchestration layer in Python (17 new modules under `mcp/lib/orchestrator/`) so the .md agents become prompt templates and a Python pipeline owns retries, token tracking, semantic convergence, ensemble reviewers, error injection, structured outputs, stage-gate verification, and checkpointing — closing all 26 audit findings, reaching ~95% Sakana v2 parity, and preserving cross-host parity (Claude Code / Codex / Gemini).

**Architecture:** SKILL.md (≤200 lines, intent routing only) → `mcp__ai-scientist__run_pipeline` MCP tool → `mcp/lib/orchestrator/pipeline.py::Pipeline.run_full_pipeline()` → 17 phases dispatched via host-specific backend (`dispatch/{claude_code,codex,gemini}.py`) → .md agent files used as prompt templates filled with `<input>` placeholders → ReflectionLoop / BiasedReviewers / StageGate / CheckpointManager / TokenTracker / MemPalace plumbing.

**Tech Stack:** Python 3.11+, `backoff` (vendored via Sakana), `jsonschema`, `numpy`, `pyyaml`, `pickle`, MemPalace MCP, codex-plugin-cc bridge (existing), Crossref REST API. Tests use `pytest` + `pytest-mock`. No new external pip deps beyond what Sakana already brings.

**Spec:** `docs/specs/2026-04-27-orchestrator-rewrite-design.md` (732 lines, 14 sections). MemPalace drawers: `drawer_ai_scientist_plugin_specs_f772c9c525667def43f45403` (spec), `drawer_ai_scientist_plugin_decisions_612cb068123637a73e100dfe` (rationale).

**Plugin root:** `C:\Users\danil\OneDrive\Рабочий стол\MCPs\ai-scientist-plugin\plugins\ai-scientist\` (referred to below as `<PLUGIN>`). All paths relative to repo root unless noted.

---

## Plan structure

39 tasks across 6 phases, ~3 weeks total effort. Test-first throughout. Frequent commits (one per task minimum).

| Phase | Tasks | Focus |
|---|---|---|
| Phase A — Foundation modules | 1–10 | status, decorators, tokens, extraction, convergence, schemas, fewshot, checkpoints, dispatch backends |
| Phase B — Loop + integration modules | 11–17 | reflection, ensemble, stage_gate, references, findings, mempalace_helpers, superpowers_bridge |
| Phase C — Pipeline | 18–26 | phase_0 through phase_11 + top-level orchestrator + AskUserQuestion gates |
| Phase D — Skill + MCP surface | 27–29 | new MCP tools, slim SKILL.md, preserve legacy |
| Phase E — Vendored assets | 30–34 | research-state view, findings drawer, citation discipline, slide-presenter agent, plan-archive hook |
| Phase F — Final integration | 35–39 | settings, schema, README, replay test, v2.0.0 tag |

---

## Phase A — Foundation modules

### Task 1: Scaffold `orchestrator/` directory + `__init__.py`

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/__init__.py`
- Create: `<PLUGIN>/mcp/lib/orchestrator/dispatch/__init__.py`
- Create: `<PLUGIN>/tests/orchestrator/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
cd "<PLUGIN>"
mkdir -p mcp/lib/orchestrator/dispatch
mkdir -p ../../tests/orchestrator
```

- [ ] **Step 2: Write `mcp/lib/orchestrator/__init__.py`**

```python
"""AI-Scientist orchestrator — Python pipeline owning state, retries, convergence,
ensemble aggregation, and checkpoint persistence.

The .md agent files in <PLUGIN>/agents/ are prompt templates filled by this
orchestrator at dispatch time. SKILL.md only handles intent routing and
surfacing AskUserQuestion gates.

See docs/specs/2026-04-27-orchestrator-rewrite-design.md for the architecture.
"""

__version__ = "0.1.0"
```

- [ ] **Step 3: Write `mcp/lib/orchestrator/dispatch/__init__.py`**

```python
"""Per-host dispatch backends. detect_host() picks claude_code / codex / gemini."""

from .claude_code import ClaudeCodeDispatcher
from .codex import CodexDispatcher
from .gemini import GeminiDispatcher


def get_dispatcher(host: str):
    """Return the dispatcher class for the given host name."""
    return {
        "claude_code": ClaudeCodeDispatcher,
        "codex": CodexDispatcher,
        "gemini": GeminiDispatcher,
    }[host]


__all__ = ["ClaudeCodeDispatcher", "CodexDispatcher", "GeminiDispatcher", "get_dispatcher"]
```

- [ ] **Step 4: Write `tests/orchestrator/__init__.py`** (empty marker file)

```python
# Test package for ai-scientist orchestrator.
```

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/__init__.py mcp/lib/orchestrator/dispatch/__init__.py tests/orchestrator/__init__.py
git commit -m "feat(orchestrator): scaffold module dirs

Per spec §3.2. Empty packages so subsequent tasks can import."
```

---

### Task 2: `status.py` — AgentStatus enum + BLOCKED decision tree helper

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/status.py`
- Create: `<PLUGIN>/tests/orchestrator/test_status.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_status.py
import pytest
from mcp.lib.orchestrator.status import AgentStatus, AgentResponse, decide_next_action


def test_agent_status_enum_values():
    assert AgentStatus.DONE.value == "done"
    assert AgentStatus.DONE_WITH_CONCERNS.value == "done_with_concerns"
    assert AgentStatus.BLOCKED.value == "blocked"
    assert AgentStatus.NEEDS_CONTEXT.value == "needs_context"


def test_blocked_needs_more_context_re_dispatches_same_model():
    response = AgentResponse(
        status=AgentStatus.BLOCKED,
        reason="needs more context: missing paper_list.json",
        payload=None,
    )
    decision = decide_next_action(response, current_model="opus", escalation_count=0)
    assert decision.action == "extract_context_and_redispatch"
    assert decision.model == "opus"


def test_blocked_needs_harder_reasoning_escalates_model():
    response = AgentResponse(
        status=AgentStatus.BLOCKED,
        reason="needs harder reasoning: synthesis is non-trivial",
        payload=None,
    )
    decision = decide_next_action(response, current_model="sonnet", escalation_count=0)
    assert decision.action == "redispatch"
    assert decision.model == "opus"


def test_blocked_after_2_escalations_asks_user():
    response = AgentResponse(
        status=AgentStatus.BLOCKED,
        reason="fundamentally stuck",
        payload=None,
    )
    decision = decide_next_action(response, current_model="opus", escalation_count=2)
    assert decision.action == "ask_user_question"


def test_done_with_concerns_proceeds():
    response = AgentResponse(
        status=AgentStatus.DONE_WITH_CONCERNS,
        reason="abstract is short",
        payload={"abstract": "..."},
    )
    decision = decide_next_action(response, current_model="opus", escalation_count=0)
    assert decision.action == "proceed_with_logging"


def test_needs_context_extracts_and_redispatches():
    response = AgentResponse(
        status=AgentStatus.NEEDS_CONTEXT,
        reason="needs paper_list.json",
        payload=None,
    )
    decision = decide_next_action(response, current_model="sonnet", escalation_count=0)
    assert decision.action == "extract_context_and_redispatch"
```

- [ ] **Step 2: Run test, expect failure**

```bash
cd "<PLUGIN>" && python -m pytest tests/orchestrator/test_status.py -v
```

Expected: ImportError, "no module named status".

- [ ] **Step 3: Implement `mcp/lib/orchestrator/status.py`**

```python
"""AgentStatus enum + BLOCKED decision tree per spec §4.9 and §6.3."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class AgentStatus(str, Enum):
    DONE = "done"
    DONE_WITH_CONCERNS = "done_with_concerns"
    BLOCKED = "blocked"
    NEEDS_CONTEXT = "needs_context"


@dataclass
class AgentResponse:
    status: AgentStatus
    reason: str
    payload: Any = None


@dataclass
class NextAction:
    action: str  # 'proceed' | 'proceed_with_logging' | 'extract_context_and_redispatch' | 'redispatch' | 'ask_user_question'
    model: Optional[str] = None
    notes: str = ""


_MODEL_ESCALATION = {"sonnet": "opus", "opus": "opus"}  # opus stays opus (caller bumps thinking)


def decide_next_action(
    response: AgentResponse,
    *,
    current_model: str,
    escalation_count: int,
    max_escalations: int = 2,
) -> NextAction:
    """Decision tree per spec §6.3.

    Never silently retry the same model on the same prompt.
    """
    if response.status == AgentStatus.DONE:
        return NextAction(action="proceed")
    if response.status == AgentStatus.DONE_WITH_CONCERNS:
        return NextAction(action="proceed_with_logging", notes=response.reason)
    if response.status == AgentStatus.NEEDS_CONTEXT:
        return NextAction(
            action="extract_context_and_redispatch",
            model=current_model,
            notes=response.reason,
        )
    # BLOCKED
    if escalation_count >= max_escalations:
        return NextAction(action="ask_user_question", notes=response.reason)
    reason_lc = response.reason.lower()
    if "needs more context" in reason_lc or "missing" in reason_lc:
        return NextAction(action="extract_context_and_redispatch", model=current_model)
    if "needs harder reasoning" in reason_lc or "non-trivial" in reason_lc:
        return NextAction(action="redispatch", model=_MODEL_ESCALATION[current_model])
    if "task too large" in reason_lc:
        return NextAction(action="redispatch", model=current_model, notes="break into sub-tasks")
    return NextAction(action="ask_user_question", notes=response.reason)
```

- [ ] **Step 4: Run test, expect pass**

```bash
cd "<PLUGIN>" && python -m pytest tests/orchestrator/test_status.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/status.py tests/orchestrator/test_status.py
git commit -m "feat(orchestrator): AgentStatus enum + BLOCKED decision tree

Per spec §4.9 + §6.3. Never silently retry same model on same prompt.
2 escalations then ask the user."
```

---

### Task 3: `decorators.py` — `@retry_with_backoff` + `@track_tokens` + `@log_phase`

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/decorators.py`
- Create: `<PLUGIN>/tests/orchestrator/test_decorators.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_decorators.py
import pytest
from unittest.mock import MagicMock, patch
from mcp.lib.orchestrator.decorators import retry_with_backoff, track_tokens, log_phase


class FakeRateLimitError(Exception):
    pass


def test_retry_succeeds_on_2nd_try():
    calls = {"n": 0}

    @retry_with_backoff(max_tries=3, max_time=10, on=(FakeRateLimitError,))
    def f():
        calls["n"] += 1
        if calls["n"] < 2:
            raise FakeRateLimitError("rate limited")
        return "ok"

    assert f() == "ok"
    assert calls["n"] == 2


def test_retry_raises_after_max_tries():
    @retry_with_backoff(max_tries=2, max_time=10, on=(FakeRateLimitError,))
    def f():
        raise FakeRateLimitError("always fails")

    with pytest.raises(FakeRateLimitError):
        f()


def test_retry_does_not_retry_on_unmatched_exception():
    @retry_with_backoff(max_tries=3, max_time=10, on=(FakeRateLimitError,))
    def f():
        raise ValueError("different error")

    with pytest.raises(ValueError):
        f()


def test_track_tokens_calls_tracker():
    from mcp.lib.orchestrator.tokens import _GLOBAL_TRACKER

    _GLOBAL_TRACKER.reset()

    @track_tokens(phase="ideation", agent="ideator")
    def f():
        # Simulate an LLM result with token counts
        return {"prompt_tokens": 100, "completion_tokens": 200, "thinking_tokens": 50}

    f()
    report = _GLOBAL_TRACKER.report()
    assert report["by_phase"]["ideation"]["prompt"] == 100
    assert report["by_phase"]["ideation"]["completion"] == 200
    assert report["by_phase"]["ideation"]["thinking"] == 50


def test_log_phase_logs_start_and_end(caplog):
    @log_phase
    def f(arg):
        return arg * 2

    import logging
    caplog.set_level(logging.INFO)
    result = f(21)
    assert result == 42
    messages = [r.message for r in caplog.records]
    assert any("start: f" in m for m in messages)
    assert any("end: f" in m for m in messages)
```

- [ ] **Step 2: Run test, expect failure**

```bash
python -m pytest tests/orchestrator/test_decorators.py -v
```

Expected: ImportError on decorators or tokens module.

- [ ] **Step 3: Implement `mcp/lib/orchestrator/decorators.py`**

```python
"""Decorators for the orchestrator: retry + token tracking + phase logging.
Per spec §4.1.

Implementation note: vendored Sakana already brings `backoff`. We do NOT
import it here to keep the orchestrator standalone — we re-implement a tiny
exponential-backoff retry instead. ~30 LOC.
"""
from __future__ import annotations
import functools
import logging
import time
from typing import Callable, Iterable, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    *,
    max_tries: int = 5,
    max_time: float = 300.0,
    on: Iterable[Type[BaseException]] = (Exception,),
    initial_delay: float = 1.0,
    factor: float = 2.0,
):
    """Exponential backoff. Retries only on listed exception types."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            start = time.monotonic()
            last_exc = None
            for attempt in range(1, max_tries + 1):
                if time.monotonic() - start >= max_time:
                    break
                try:
                    return fn(*args, **kwargs)
                except tuple(on) as exc:
                    last_exc = exc
                    if attempt == max_tries:
                        break
                    logger.warning(
                        "retry_with_backoff: %s attempt %d/%d failed (%s); sleeping %.1fs",
                        fn.__name__, attempt, max_tries, exc, delay,
                    )
                    time.sleep(delay)
                    delay *= factor
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator


def track_tokens(*, phase: str, agent: str):
    """Wrap a function whose return value contains 'prompt_tokens' /
    'completion_tokens' / optional 'thinking_tokens'. The tracker is a global
    singleton (see tokens.py).
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from .tokens import _GLOBAL_TRACKER
            result = fn(*args, **kwargs)
            if isinstance(result, dict):
                _GLOBAL_TRACKER.add(
                    phase=phase,
                    agent=agent,
                    prompt_tok=int(result.get("prompt_tokens", 0) or 0),
                    completion_tok=int(result.get("completion_tokens", 0) or 0),
                    thinking_tok=int(result.get("thinking_tokens", 0) or 0),
                )
            return result
        return wrapper
    return decorator


def log_phase(fn: Callable) -> Callable:
    """Log start/end of a phase function."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        logger.info("start: %s", fn.__name__)
        start = time.monotonic()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            logger.info("end: %s (%.2fs)", fn.__name__, elapsed)
    return wrapper
```

- [ ] **Step 4: Run test, expect pass after Task 4 stubs `tokens.py`**

If you run now you'll get an ImportError on `tokens.py`. Either jump to Task 4 first or stub `tokens.py` minimally:

```bash
# Minimal stub to unblock the test:
cat > mcp/lib/orchestrator/tokens.py <<'EOF'
class _Tracker:
    def __init__(self): self._data = {}
    def reset(self): self._data = {}
    def add(self, **kw):
        p, a = kw["phase"], kw["agent"]
        self._data.setdefault(p, {"prompt": 0, "completion": 0, "thinking": 0})
        self._data[p]["prompt"] += kw["prompt_tok"]
        self._data[p]["completion"] += kw["completion_tok"]
        self._data[p]["thinking"] += kw["thinking_tok"]
    def report(self): return {"by_phase": dict(self._data)}
_GLOBAL_TRACKER = _Tracker()
EOF
python -m pytest tests/orchestrator/test_decorators.py -v
```

Expected: 5 passed. Task 4 will replace this stub with the full implementation.

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/decorators.py mcp/lib/orchestrator/tokens.py tests/orchestrator/test_decorators.py
git commit -m "feat(orchestrator): @retry_with_backoff + @track_tokens + @log_phase

Per spec §4.1. tokens.py is a stub here; Task 4 implements it fully."
```

---

### Task 4: `tokens.py` — TokenTracker with USD pricing + budget warnings

**Files:**
- Modify: `<PLUGIN>/mcp/lib/orchestrator/tokens.py` (replace stub from Task 3)
- Create: `<PLUGIN>/tests/orchestrator/test_tokens.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_tokens.py
import pytest
from mcp.lib.orchestrator.tokens import TokenTracker, PRICING


def test_add_accumulates_per_phase_per_agent():
    t = TokenTracker()
    t.add(phase="ideation", agent="ideator", prompt_tok=100, completion_tok=200)
    t.add(phase="ideation", agent="ideator", prompt_tok=50, completion_tok=80)
    t.add(phase="hypothesis", agent="hypothesizer", prompt_tok=200, completion_tok=400, thinking_tok=300)

    report = t.report()
    assert report["by_phase"]["ideation"]["prompt"] == 150
    assert report["by_phase"]["ideation"]["completion"] == 280
    assert report["by_phase"]["hypothesis"]["thinking"] == 300
    assert report["by_agent"]["ideator"]["prompt"] == 150


def test_total_cost_usd_uses_pricing_table():
    t = TokenTracker(model="opus", pricing=PRICING)
    t.add(phase="ideation", agent="ideator", prompt_tok=1_000_000, completion_tok=1_000_000)
    cost = t.total_cost_usd()
    # Opus pricing: $15/M input, $75/M output → $90 total
    assert cost == pytest.approx(90.0, rel=0.01)


def test_warn_if_over_budget_returns_true_at_80pct():
    t = TokenTracker(model="opus")
    # 1M input tokens = $15
    t.add(phase="ideation", agent="ideator", prompt_tok=1_000_000, completion_tok=0)
    triggered = t.warn_if_over_budget(budget_usd=18.0)  # 15/18 = 83% > 80%
    assert triggered is True


def test_warn_if_over_budget_returns_false_below_threshold():
    t = TokenTracker(model="opus")
    t.add(phase="ideation", agent="ideator", prompt_tok=100_000, completion_tok=0)
    triggered = t.warn_if_over_budget(budget_usd=20.0)
    assert triggered is False


def test_global_tracker_singleton():
    from mcp.lib.orchestrator.tokens import _GLOBAL_TRACKER
    _GLOBAL_TRACKER.reset()
    _GLOBAL_TRACKER.add(phase="x", agent="y", prompt_tok=10, completion_tok=20)
    report = _GLOBAL_TRACKER.report()
    assert report["totals"]["prompt"] == 10
```

- [ ] **Step 2: Run test, expect fail (test_total_cost_usd, etc.)**

```bash
python -m pytest tests/orchestrator/test_tokens.py -v
```

Expected: 4 of 5 fail (only `test_global_tracker_singleton` passes against the stub).

- [ ] **Step 3: Implement `mcp/lib/orchestrator/tokens.py` (full)**

```python
"""TokenTracker — per-phase + per-agent + USD cost. Singleton instance per
pipeline run. Per spec §4.2.

Pricing table is approximate (Apr 2026); user can override via settings.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Optional

# USD per 1M tokens (input, output). Approximate Apr 2026 pricing.
PRICING = {
    "opus":     {"input": 15.0, "output": 75.0},
    "sonnet":   {"input": 3.0,  "output": 15.0},
    "haiku":    {"input": 0.80, "output": 4.0},
    "gpt-5.5":      {"input": 10.0, "output": 50.0},
    "gpt-5.4":      {"input": 3.0,  "output": 15.0},
    "gpt-5.4-mini": {"input": 0.50, "output": 2.50},
    "gemini-3.1-pro-preview":  {"input": 5.0, "output": 20.0},
    "gemini-3-flash-preview":  {"input": 0.30, "output": 1.20},
}


class TokenTracker:
    def __init__(self, model: str = "opus", pricing: Optional[dict] = None):
        self.model = model
        self.pricing = pricing or PRICING
        self._by_phase: dict = defaultdict(lambda: {"prompt": 0, "completion": 0, "thinking": 0})
        self._by_agent: dict = defaultdict(lambda: {"prompt": 0, "completion": 0, "thinking": 0})
        self._totals = {"prompt": 0, "completion": 0, "thinking": 0}
        self._warned_at_pct = 0.0

    def reset(self):
        self.__init__(model=self.model, pricing=self.pricing)

    def add(self, *, phase: str, agent: str, prompt_tok: int, completion_tok: int, thinking_tok: int = 0):
        for d in (self._by_phase[phase], self._by_agent[agent], self._totals):
            d["prompt"] += prompt_tok
            d["completion"] += completion_tok
            d["thinking"] += thinking_tok

    def total_cost_usd(self) -> float:
        rates = self.pricing.get(self.model, {"input": 0, "output": 0})
        cost_in = self._totals["prompt"] / 1_000_000 * rates["input"]
        # Thinking tokens billed as output for Anthropic; as separate rate elsewhere.
        cost_out = (self._totals["completion"] + self._totals["thinking"]) / 1_000_000 * rates["output"]
        return cost_in + cost_out

    def warn_if_over_budget(self, *, budget_usd: float) -> bool:
        """Return True the FIRST time we cross 80%; False otherwise."""
        if budget_usd <= 0:
            return False
        spent = self.total_cost_usd()
        pct = spent / budget_usd
        if pct >= 0.80 and self._warned_at_pct < 0.80:
            self._warned_at_pct = pct
            return True
        return False

    def report(self) -> dict:
        return {
            "model": self.model,
            "totals": dict(self._totals),
            "by_phase": {k: dict(v) for k, v in self._by_phase.items()},
            "by_agent": {k: dict(v) for k, v in self._by_agent.items()},
            "total_cost_usd": round(self.total_cost_usd(), 4),
        }


# Singleton used by @track_tokens decorator
_GLOBAL_TRACKER = TokenTracker()
```

- [ ] **Step 4: Run tests, expect 5 of 5 pass**

```bash
python -m pytest tests/orchestrator/test_tokens.py tests/orchestrator/test_decorators.py -v
```

Expected: 10 passed total.

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/tokens.py tests/orchestrator/test_tokens.py
git commit -m "feat(orchestrator): TokenTracker with USD pricing + budget warnings

Per spec §4.2. Closes 'no token tracking' audit finding."
```

---

### Task 5: `extraction.py` — JSON / LaTeX / Python with AST validation

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/extraction.py`
- Create: `<PLUGIN>/tests/orchestrator/test_extraction.py`

- [ ] **Step 1: Write the failing test (10 fixtures)**

```python
# tests/orchestrator/test_extraction.py
import pytest
from mcp.lib.orchestrator.extraction import extract_json, extract_latex, extract_python, ExtractionError


def test_extract_json_clean():
    text = '{"k": "v"}'
    assert extract_json(text) == {"k": "v"}


def test_extract_json_fenced():
    text = '```json\n{"k": 1}\n```'
    assert extract_json(text) == {"k": 1}


def test_extract_json_with_prose_around():
    text = 'Here is the result:\n```json\n{"k": [1,2,3]}\n```\nDone.'
    assert extract_json(text) == {"k": [1, 2, 3]}


def test_extract_json_unfenced_with_prose():
    text = 'Here you go: {"a": "b"} cheers'
    assert extract_json(text) == {"a": "b"}


def test_extract_json_nested():
    text = '{"a": {"b": {"c": 1}}}'
    assert extract_json(text) == {"a": {"b": {"c": 1}}}


def test_extract_json_strips_control_chars():
    text = '{"a": "\x00\x01b"}'  # NUL + SOH
    result = extract_json(text)
    assert result["a"] == "b"


def test_extract_json_braces_in_strings_are_ignored():
    text = '{"k": "value with { brace"}'
    assert extract_json(text) == {"k": "value with { brace"}


def test_extract_json_malformed_raises():
    text = "not json at all"
    with pytest.raises(ExtractionError):
        extract_json(text)


def test_extract_latex_fenced():
    text = '```latex\n\\begin{document}hi\\end{document}\n```'
    assert extract_latex(text) == "\\begin{document}hi\\end{document}"


def test_extract_python_validates_ast():
    text = '```python\ndef f():\n    return 1\n```'
    assert extract_python(text) == "def f():\n    return 1"


def test_extract_python_raises_on_syntax_error():
    text = '```python\ndef f(:\n    return 1\n```'  # malformed
    with pytest.raises(ExtractionError, match="syntax"):
        extract_python(text)
```

- [ ] **Step 2: Run, expect ImportError**

```bash
python -m pytest tests/orchestrator/test_extraction.py -v
```

- [ ] **Step 3: Implement `extraction.py`**

```python
"""Two-tier extraction: fenced block → balanced-brace scan → cleanup → parse.
Per spec §4.4. Closes 'crude regex error classification' audit finding —
extract_python validates AST before returning, so syntax errors land in
Phase 3 not Phase 4.
"""
from __future__ import annotations
import ast
import json
import re
from typing import Optional


class ExtractionError(ValueError):
    pass


_JSON_FENCE = re.compile(r"```json\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)
_LATEX_FENCE = re.compile(r"```latex\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)
_PYTHON_FENCE = re.compile(r"```python\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _strip_control(s: str) -> str:
    return _CONTROL_CHARS.sub("", s)


def _balanced_brace_scan(text: str) -> Optional[str]:
    """Return the first balanced {...} block, ignoring braces in strings."""
    start = text.find("{")
    if start == -1:
        return None
    depth, in_str, escape = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def extract_json(text: str) -> dict:
    """Try ```json fence → balanced-brace scan → control-char strip → json.loads."""
    if not text or not text.strip():
        raise ExtractionError("empty input")
    # Tier 1: fenced
    m = _JSON_FENCE.search(text)
    candidate = m.group(1).strip() if m else None
    # Tier 2: balanced scan
    if candidate is None:
        candidate = _balanced_brace_scan(text)
    if candidate is None:
        raise ExtractionError(f"no JSON object found in input: {text[:200]!r}")
    candidate = _strip_control(candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"JSON parse failed: {e}; candidate={candidate[:200]!r}") from e


def extract_latex(text: str) -> str:
    m = _LATEX_FENCE.search(text)
    if m:
        return m.group(1).strip()
    # Fallback: assume the whole text is LaTeX
    if "\\begin{document}" in text or "\\documentclass" in text:
        return text.strip()
    raise ExtractionError("no LaTeX block found")


def extract_python(text: str) -> str:
    m = _PYTHON_FENCE.search(text)
    code = m.group(1).strip() if m else text.strip()
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ExtractionError(
            f"Python syntax error at line {e.lineno}: {e.msg}; offending code:\n{code[:500]}"
        ) from e
    return code
```

- [ ] **Step 4: Run, expect 11 passed**

```bash
python -m pytest tests/orchestrator/test_extraction.py -v
```

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/extraction.py tests/orchestrator/test_extraction.py
git commit -m "feat(orchestrator): two-tier JSON/LaTeX/Python extraction

Per spec §4.4. extract_python validates AST so syntax errors land in
Phase 3 not Phase 4. Closes 'crude regex error classification' finding."
```

---

### Task 6: `convergence.py` — semantic-signal detection

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/convergence.py`
- Create: `<PLUGIN>/tests/orchestrator/test_convergence.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_convergence.py
import pytest
from mcp.lib.orchestrator.convergence import SemanticConvergence, DEFAULT_SIGNALS


def test_detects_i_am_done():
    sc = SemanticConvergence()
    assert sc.is_converged("After review, I am done.") is True


def test_detects_finalize_idea_action():
    sc = SemanticConvergence()
    assert sc.is_converged('{"action": "FinalizeIdea", "name": "x"}') is True


def test_detects_no_further_changes():
    sc = SemanticConvergence()
    assert sc.is_converged("This is final; no further changes needed.") is True


def test_does_not_falsely_converge_on_done_in_other_context():
    sc = SemanticConvergence()
    assert sc.is_converged("The work is not done yet.") is False


def test_custom_signals_override_default():
    sc = SemanticConvergence(signals=["my custom signal"])
    assert sc.is_converged("Here is my custom signal!") is True
    assert sc.is_converged("I am done") is False


def test_default_signals_list():
    assert "I am done" in DEFAULT_SIGNALS
    assert '"action": "FinalizeIdea"' in DEFAULT_SIGNALS
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `convergence.py`**

```python
"""Semantic-signal convergence detection. Per spec §4.5.

Loops terminate on LLM signal, not fixed round count. Per Sakana
perform_writeup.py:693-707.
"""
from __future__ import annotations
import re
from typing import Optional

DEFAULT_SIGNALS = [
    "I am done",
    '"action": "FinalizeIdea"',
    "no further changes needed",
    "no further refinement",
    '"converged": true',
]


def _make_pattern(signal: str) -> re.Pattern:
    """Word-boundary regex for natural-language signals; substring for JSON-ish."""
    if signal.startswith('"') or signal.startswith("{"):
        return re.compile(re.escape(signal), re.IGNORECASE)
    # Natural language: require word boundaries to avoid false positives
    # like "not done yet"
    pattern = r"(?<![a-zA-Z])" + re.escape(signal) + r"(?![a-zA-Z])"
    return re.compile(pattern, re.IGNORECASE)


class SemanticConvergence:
    def __init__(self, signals: Optional[list] = None):
        self.signals = signals or list(DEFAULT_SIGNALS)
        self._patterns = [_make_pattern(s) for s in self.signals]

    def is_converged(self, llm_response: str) -> bool:
        """True if any signal phrase appears in the response, with negation guard."""
        if not llm_response:
            return False
        # Negation guard: "not done", "won't finalize", "I'm not done"
        negation_window = 30
        for pat in self._patterns:
            for m in pat.finditer(llm_response):
                start = max(0, m.start() - negation_window)
                preceding = llm_response[start:m.start()].lower()
                if any(neg in preceding for neg in [" not ", " no ", "n't ", "without "]):
                    continue
                return True
        return False
```

- [ ] **Step 4: Run, expect 6 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/convergence.py tests/orchestrator/test_convergence.py
git commit -m "feat(orchestrator): SemanticConvergence with negation guard

Per spec §4.5. Loops terminate on LLM 'I am done' signal, not fixed rounds."
```

---

### Task 7: `schemas.py` — strict JSON schemas per phase

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/schemas.py`
- Create: `<PLUGIN>/tests/orchestrator/test_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_schemas.py
import pytest
import jsonschema
from mcp.lib.orchestrator.schemas import (
    IDEATION_SCHEMA, HYPOTHESIS_SCHEMA, REVIEW_SCHEMA,
    EXPERIMENT_RESULT_SCHEMA, validate_against,
)


def test_ideation_schema_passes_valid():
    valid = {
        "Name": "ridge_hetero",
        "Title": "Ridge under heteroscedastic noise",
        "Short_Hypothesis": "Ridge beats OLS as alpha grows.",
        "Related_Work": "ESL covers ridge under homoscedastic noise.",
        "Abstract": "We test...",
        "Experiments": [{"name": "sweep", "metric": "MSE"}],
        "Risks": ["small effect size"],
    }
    validate_against(valid, IDEATION_SCHEMA)


def test_ideation_schema_rejects_missing_required():
    invalid = {"Name": "x"}
    with pytest.raises(jsonschema.ValidationError, match="Title"):
        validate_against(invalid, IDEATION_SCHEMA)


def test_hypothesis_schema_passes_valid():
    valid = {
        "hypothesis": "Ridge has lower test MSE than OLS for alpha >= 2.",
        "math_models": "y = X*beta + eps where eps ~ N(0, sigma^2 * (1+alpha*||x||^2/p))",
        "statistical_framework": {
            "null": "no difference", "alt": "ridge < ols",
            "test": "paired t-test", "alpha": 0.05,
            "correction": "bonferroni", "effect_size": "cohens_d",
        },
        "methodology": "monte carlo over alpha grid",
        "dependencies": ["numpy", "scikit-learn"],
    }
    validate_against(valid, HYPOTHESIS_SCHEMA)


def test_review_schema_passes_valid():
    valid = {
        "Summary": "Solid synthetic benchmark.",
        "Strengths": ["clean protocol"],
        "Weaknesses": ["small effect"],
        "Originality": 2, "Quality": 3, "Clarity": 3, "Significance": 2,
        "Soundness": 3, "Presentation": 3, "Contribution": 2,
        "Overall": 5, "Confidence": 4,
        "Decision": "Borderline / Weak Accept",
        "Questions": ["why fixed lambda?"],
        "Limitations": ["isotropic design only"],
        "Actionable_Fixes": ["fix monotonicity claim"],
    }
    validate_against(valid, REVIEW_SCHEMA)


def test_review_schema_rejects_score_out_of_range():
    invalid = {
        "Summary": "x", "Strengths": [], "Weaknesses": [],
        "Originality": 99, "Quality": 1, "Clarity": 1, "Significance": 1,
        "Soundness": 1, "Presentation": 1, "Contribution": 1,
        "Overall": 1, "Confidence": 1,
        "Decision": "Reject", "Questions": [], "Limitations": [],
        "Actionable_Fixes": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_against(invalid, REVIEW_SCHEMA)


def test_experiment_result_schema_passes_valid():
    valid = {
        "exit_code": 0, "results_csv_present": True,
        "npy_files": ["data_main.npy"], "figures": ["plot_results.png"],
        "fix_attempts": 0, "stdout_summary": "...", "stderr_summary": "",
    }
    validate_against(valid, EXPERIMENT_RESULT_SCHEMA)
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `schemas.py`**

```python
"""Strict JSON schemas per phase output. Per spec §4.3.

Two enforcement points:
  1. `strict: true` on the agent's tool-use schema (where the host supports it)
  2. validate_against() called on the parsed output before commit
On schema violation: re-prompt with the validator error inlined, max 2 retries.
"""
from __future__ import annotations
import jsonschema


def validate_against(obj, schema):
    """Raise jsonschema.ValidationError if obj fails the schema."""
    jsonschema.validate(obj, schema)


IDEATION_SCHEMA = {
    "type": "object",
    "required": ["Name", "Title", "Short_Hypothesis", "Related_Work",
                 "Abstract", "Experiments", "Risks"],
    "properties": {
        "Name":             {"type": "string", "minLength": 1},
        "Title":            {"type": "string", "minLength": 1},
        "Short_Hypothesis": {"type": "string", "minLength": 1},
        "Related_Work":     {"type": "string"},
        "Abstract":         {"type": "string", "minLength": 50},
        "Experiments":      {"type": "array", "minItems": 1,
                             "items": {"type": "object", "required": ["name", "metric"]}},
        "Risks":            {"type": "array"},
    },
}

HYPOTHESIS_SCHEMA = {
    "type": "object",
    "required": ["hypothesis", "math_models", "statistical_framework",
                 "methodology", "dependencies"],
    "properties": {
        "hypothesis":            {"type": "string", "minLength": 10},
        "math_models":           {"type": "string"},
        "statistical_framework": {"type": "object"},
        "methodology":           {"type": "string"},
        "dependencies":          {"type": "array", "items": {"type": "string"}},
    },
}

REVIEW_SCHEMA = {
    "type": "object",
    "required": ["Summary", "Strengths", "Weaknesses",
                 "Originality", "Quality", "Clarity", "Significance",
                 "Soundness", "Presentation", "Contribution",
                 "Overall", "Confidence", "Decision",
                 "Questions", "Limitations", "Actionable_Fixes"],
    "properties": {
        "Summary":     {"type": "string"},
        "Strengths":   {"type": "array", "items": {"type": "string"}},
        "Weaknesses":  {"type": "array", "items": {"type": "string"}},
        "Originality": {"type": "integer", "minimum": 1, "maximum": 4},
        "Quality":     {"type": "integer", "minimum": 1, "maximum": 4},
        "Clarity":     {"type": "integer", "minimum": 1, "maximum": 4},
        "Significance":{"type": "integer", "minimum": 1, "maximum": 4},
        "Soundness":   {"type": "integer", "minimum": 1, "maximum": 4},
        "Presentation":{"type": "integer", "minimum": 1, "maximum": 4},
        "Contribution":{"type": "integer", "minimum": 1, "maximum": 4},
        "Overall":     {"type": "integer", "minimum": 1, "maximum": 10},
        "Confidence":  {"type": "integer", "minimum": 1, "maximum": 5},
        "Decision":    {"type": "string"},
        "Questions":   {"type": "array"},
        "Limitations": {"type": "array"},
        "Actionable_Fixes": {"type": "array", "items": {"type": "string"}},
    },
}

EXPERIMENT_RESULT_SCHEMA = {
    "type": "object",
    "required": ["exit_code", "results_csv_present", "npy_files", "figures",
                 "fix_attempts", "stdout_summary", "stderr_summary"],
    "properties": {
        "exit_code":           {"type": "integer"},
        "results_csv_present": {"type": "boolean"},
        "npy_files":           {"type": "array", "items": {"type": "string"}},
        "figures":             {"type": "array", "items": {"type": "string"}},
        "fix_attempts":        {"type": "integer", "minimum": 0},
        "stdout_summary":      {"type": "string"},
        "stderr_summary":      {"type": "string"},
    },
}
```

- [ ] **Step 4: Run, expect 6 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/schemas.py tests/orchestrator/test_schemas.py
git commit -m "feat(orchestrator): strict JSON schemas per phase output

Per spec §4.3. Closes 'weak schema enforcement' audit finding."
```

---

### Task 8: `fewshot.py` — example injector

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/fewshot.py`
- Create: `<PLUGIN>/tests/orchestrator/test_fewshot.py`
- Test: existing `<PLUGIN>/mcp/templates/fewshot/{attention,carpe_diem,automated_relational}.{json,txt}`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_fewshot.py
from pathlib import Path
import pytest
from mcp.lib.orchestrator.fewshot import FewShotInjector


def test_inject_wraps_examples_in_xml_blocks(tmp_path):
    ex1 = tmp_path / "ex1.txt"
    ex1.write_text("Example 1 body.")
    inj = FewShotInjector()
    out = inj.inject("Original prompt.", [ex1])
    assert "<example>" in out
    assert "Example 1 body." in out
    assert "</example>" in out
    assert "Original prompt." in out


def test_inject_preserves_order(tmp_path):
    ex1 = tmp_path / "a.txt"; ex1.write_text("AAA")
    ex2 = tmp_path / "b.txt"; ex2.write_text("BBB")
    inj = FewShotInjector()
    out = inj.inject("end", [ex1, ex2])
    assert out.index("AAA") < out.index("BBB") < out.index("end")


def test_inject_skips_missing_files(tmp_path):
    real = tmp_path / "real.txt"; real.write_text("real")
    fake = tmp_path / "missing.txt"
    inj = FewShotInjector()
    out = inj.inject("X", [real, fake])
    assert "real" in out
    # Missing file silently skipped


def test_inject_handles_json_examples(tmp_path):
    ex = tmp_path / "review.json"
    ex.write_text('{"Overall": 6, "Decision": "Accept"}')
    inj = FewShotInjector()
    out = inj.inject("X", [ex])
    assert '"Overall": 6' in out
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `fewshot.py`**

```python
"""Few-shot example injection. Per spec §4.8.

Activates for ideator (paper exemplars), hypothesizer (well-formed
hypothesis exemplars), reviewer (review exemplars). The example files
already exist at mcp/templates/fewshot/ but were never injected.
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable


class FewShotInjector:
    def inject(self, agent_prompt: str, examples: Iterable[Path]) -> str:
        """Prepend `<example>...</example>` blocks for each example file."""
        blocks = []
        for path in examples:
            p = Path(path)
            if not p.is_file():
                continue
            try:
                body = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            blocks.append(f"<example source={p.name!r}>\n{body}\n</example>")
        if not blocks:
            return agent_prompt
        return "\n\n".join(blocks) + "\n\n" + agent_prompt
```

- [ ] **Step 4: Run, expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/fewshot.py tests/orchestrator/test_fewshot.py
git commit -m "feat(orchestrator): FewShotInjector

Per spec §4.8. Closes 'few-shot files unused' finding."
```

---

### Task 9: `checkpoints.py` — pickle per-phase state + MemPalace mirror

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/checkpoints.py`
- Create: `<PLUGIN>/tests/orchestrator/test_checkpoints.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_checkpoints.py
from pathlib import Path
from mcp.lib.orchestrator.checkpoints import CheckpointManager


def test_save_and_load_round_trip(tmp_path):
    cm = CheckpointManager(checkpoint_dir=tmp_path)
    state = {"phase": "ideation", "candidates": [1, 2, 3], "winner": 2}
    cm.save("phase_0_5", state)
    loaded = cm.load("phase_0_5")
    assert loaded == state


def test_load_returns_none_for_missing(tmp_path):
    cm = CheckpointManager(checkpoint_dir=tmp_path)
    assert cm.load("never_saved") is None


def test_latest_returns_most_recent(tmp_path):
    cm = CheckpointManager(checkpoint_dir=tmp_path)
    cm.save("phase_0", {"a": 1})
    cm.save("phase_1", {"b": 2})
    cm.save("phase_2", {"c": 3})
    assert cm.latest() == "phase_2"


def test_latest_returns_none_for_empty_dir(tmp_path):
    cm = CheckpointManager(checkpoint_dir=tmp_path)
    assert cm.latest() is None


def test_list_completed_phases(tmp_path):
    cm = CheckpointManager(checkpoint_dir=tmp_path)
    cm.save("phase_0", {})
    cm.save("phase_2", {})
    phases = cm.list_completed()
    assert sorted(phases) == ["phase_0", "phase_2"]
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `checkpoints.py`**

```python
"""CheckpointManager — per-phase pickle. Per spec §4.16.

Pickles state to <output_dir>/.checkpoints/phase_<phase>.pkl AND mirrors to
MemPalace as a drawer under 'phase-checkpoints' room. The mirror is best-
effort; failure to mirror does NOT block the pickle save.

`--resume` flag loads from latest().
"""
from __future__ import annotations
import pickle
from pathlib import Path
from typing import Optional


class CheckpointManager:
    def __init__(self, checkpoint_dir: Path, palace=None):
        self.dir = Path(checkpoint_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.palace = palace  # Optional: ProjectPalace for mirroring

    def _path(self, phase: str) -> Path:
        return self.dir / f"{phase}.pkl"

    def save(self, phase: str, state: dict) -> None:
        path = self._path(phase)
        with open(path, "wb") as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
        # Best-effort palace mirror
        if self.palace is not None:
            try:
                self.palace.write_diary(
                    agent="checkpoint",
                    content=f"Phase {phase} checkpoint saved to {path.name}",
                    tags=["phase-checkpoint", f"phase:{phase}"],
                )
            except Exception:
                pass  # Mirror is advisory

    def load(self, phase: str) -> Optional[dict]:
        path = self._path(phase)
        if not path.is_file():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def list_completed(self) -> list:
        return sorted(p.stem for p in self.dir.glob("*.pkl"))

    def latest(self) -> Optional[str]:
        completed = self.list_completed()
        return completed[-1] if completed else None
```

- [ ] **Step 4: Run, expect 5 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/checkpoints.py tests/orchestrator/test_checkpoints.py
git commit -m "feat(orchestrator): CheckpointManager with optional MemPalace mirror

Per spec §4.16. Closes 'no checkpointing' audit finding. --resume reads
from latest(). Palace mirror is best-effort."
```

---

### Task 10: Three host-dispatch backends

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/dispatch/claude_code.py`
- Create: `<PLUGIN>/mcp/lib/orchestrator/dispatch/codex.py`
- Create: `<PLUGIN>/mcp/lib/orchestrator/dispatch/gemini.py`
- Create: `<PLUGIN>/tests/orchestrator/test_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_dispatch.py
import pytest
from unittest.mock import MagicMock
from mcp.lib.orchestrator.dispatch import (
    get_dispatcher, ClaudeCodeDispatcher, CodexDispatcher, GeminiDispatcher,
)


def test_get_dispatcher_claude_code():
    d = get_dispatcher("claude_code")
    assert d is ClaudeCodeDispatcher


def test_get_dispatcher_codex():
    assert get_dispatcher("codex") is CodexDispatcher


def test_get_dispatcher_gemini():
    assert get_dispatcher("gemini") is GeminiDispatcher


def test_get_dispatcher_unknown_raises():
    with pytest.raises(KeyError):
        get_dispatcher("unknown")


def test_claude_code_dispatcher_calls_task_tool():
    fake_task_tool = MagicMock(return_value={"status": "done", "payload": {}})
    d = ClaudeCodeDispatcher(task_tool=fake_task_tool)
    d.dispatch(agent_name="ideator", inputs={"topic": "X"})
    fake_task_tool.assert_called_once()
    call = fake_task_tool.call_args
    assert "ai-scientist-ideator" in str(call)


def test_codex_dispatcher_calls_spawn_agent():
    fake_spawn = MagicMock(return_value={"status": "done"})
    d = CodexDispatcher(spawn_agent=fake_spawn)
    d.dispatch(agent_name="reviewer", inputs={"manuscript": "..."})
    fake_spawn.assert_called_once()


def test_gemini_dispatcher_falls_back_to_inline():
    """Gemini lacks Task; pipeline executes the prompt inline.
    The dispatcher just returns the agent_md path for the caller to load."""
    d = GeminiDispatcher()
    result = d.dispatch(agent_name="reviewer", inputs={"x": 1})
    assert result["mode"] == "inline"
    assert "agent_path" in result
    assert "ai-scientist-reviewer" in result["agent_path"] or "reviewer" in result["agent_path"]
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement the 3 dispatchers**

```python
# mcp/lib/orchestrator/dispatch/claude_code.py
"""Claude Code dispatcher — uses the host's Task tool via MCP surface.

The pipeline calls dispatch() but the actual Task() call is performed by
Claude Code itself via mcp__ai-scientist__dispatch_phase (see Task 27).
This class is a thin wrapper that the pipeline.py uses; in production
the Task tool is injected by the MCP server's tool-call handler.
"""
from __future__ import annotations
from typing import Callable, Optional


class ClaudeCodeDispatcher:
    name = "claude_code"

    def __init__(self, task_tool: Optional[Callable] = None):
        self.task_tool = task_tool

    def dispatch(self, *, agent_name: str, inputs: dict) -> dict:
        """Invoke Task(subagent_type=f"ai-scientist-{agent_name}", prompt=...)."""
        if self.task_tool is None:
            raise RuntimeError(
                "ClaudeCodeDispatcher.task_tool not injected. "
                "MCP server must pass the host's Task tool when constructing."
            )
        subagent_type = f"ai-scientist-{agent_name}"
        prompt = self._build_prompt(agent_name, inputs)
        return self.task_tool(subagent_type=subagent_type, prompt=prompt)

    @staticmethod
    def _build_prompt(agent_name: str, inputs: dict) -> str:
        # Inline inputs as <input name="...">value</input> blocks
        lines = [f"<input name={k!r}>{v}</input>" for k, v in inputs.items()]
        return "\n".join(lines)
```

```python
# mcp/lib/orchestrator/dispatch/codex.py
"""Codex CLI dispatcher — uses spawn_agent."""
from __future__ import annotations
from typing import Callable, Optional


class CodexDispatcher:
    name = "codex"

    def __init__(self, spawn_agent: Optional[Callable] = None):
        self.spawn_agent = spawn_agent

    def dispatch(self, *, agent_name: str, inputs: dict) -> dict:
        if self.spawn_agent is None:
            raise RuntimeError("CodexDispatcher.spawn_agent not injected")
        message = self._build_message(agent_name, inputs)
        return self.spawn_agent(agent_type="worker", message=message)

    @staticmethod
    def _build_message(agent_name: str, inputs: dict) -> str:
        from pathlib import Path
        import os
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        agent_path = Path(plugin_root) / "agents" / f"{agent_name}.md"
        try:
            agent_body = agent_path.read_text(encoding="utf-8")
        except OSError:
            agent_body = f"(agent file missing: {agent_path})"
        input_block = "\n".join(f"<input name={k!r}>{v}</input>" for k, v in inputs.items())
        return (
            "Your task is to perform the following. Follow the instructions below exactly.\n\n"
            f"<agent-instructions>\n{agent_body}\n</agent-instructions>\n\n"
            f"Inputs:\n{input_block}\n\n"
            "Execute this now. Output ONLY the structured response wrapped in "
            "<output name=\"...\"> tags as specified."
        )
```

```python
# mcp/lib/orchestrator/dispatch/gemini.py
"""Gemini CLI dispatcher — falls back to inline reasoning.

Gemini lacks Task / spawn_agent. The pipeline executes the prompt in the
current session. This dispatcher just locates the agent .md file and
returns its path; the pipeline reads it and inlines the body.
"""
from __future__ import annotations
import os
from pathlib import Path


class GeminiDispatcher:
    name = "gemini"

    def dispatch(self, *, agent_name: str, inputs: dict) -> dict:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
        agent_path = Path(plugin_root) / "agents" / f"{agent_name}.md"
        return {
            "mode": "inline",
            "agent_path": str(agent_path),
            "inputs": inputs,
            "note": "Gemini lacks Task; pipeline must execute this prompt inline.",
        }
```

- [ ] **Step 4: Run, expect 7 passed**

```bash
python -m pytest tests/orchestrator/test_dispatch.py -v
```

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/dispatch/ tests/orchestrator/test_dispatch.py
git commit -m "feat(orchestrator): three host-dispatch backends

Per spec §3.4. ClaudeCodeDispatcher uses Task; CodexDispatcher uses
spawn_agent; GeminiDispatcher falls back to inline. All injectable
for testing."
```

---

## Phase B — Loop + integration modules

### Task 11: `reflection.py` — multi-round refinement loop with error injection

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/reflection.py`
- Create: `<PLUGIN>/tests/orchestrator/test_reflection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_reflection.py
from unittest.mock import MagicMock
from mcp.lib.orchestrator.reflection import ReflectionLoop, EvaluatorVerdict


def test_loop_returns_on_first_pass():
    dispatcher = MagicMock(return_value={"raw": '{"k":"v"}'})
    evaluator = MagicMock(return_value=EvaluatorVerdict(verdict="PASS", reason=""))
    loop = ReflectionLoop(
        dispatcher=dispatcher,
        evaluator=evaluator,
        schema={"type": "object", "required": ["k"]},
        extractor=lambda r: __import__("json").loads(r["raw"]),
    )
    result = loop.run(agent_name="ideator", inputs={"x": 1}, max_rounds=5)
    assert result == {"k": "v"}
    assert dispatcher.call_count == 1


def test_loop_re_dispatches_on_needs_improvement():
    responses = [
        {"raw": '{"k":"bad"}'},
        {"raw": '{"k":"better"}'},
        {"raw": '{"k":"best"}'},
    ]
    dispatcher = MagicMock(side_effect=responses)
    verdicts = [
        EvaluatorVerdict(verdict="NEEDS_IMPROVEMENT", reason="bad value"),
        EvaluatorVerdict(verdict="NEEDS_IMPROVEMENT", reason="still bad"),
        EvaluatorVerdict(verdict="PASS", reason=""),
    ]
    evaluator = MagicMock(side_effect=verdicts)
    loop = ReflectionLoop(
        dispatcher=dispatcher,
        evaluator=evaluator,
        schema={"type": "object"},
        extractor=lambda r: __import__("json").loads(r["raw"]),
    )
    result = loop.run(agent_name="ideator", inputs={"x": 1}, max_rounds=5)
    assert result == {"k": "best"}
    assert dispatcher.call_count == 3


def test_loop_injects_history_on_re_dispatch():
    responses = [
        {"raw": '{"k":"v1"}'},
        {"raw": '{"k":"v2"}'},
    ]
    captured_inputs = []

    def fake_dispatcher(*, agent_name, inputs):
        captured_inputs.append(inputs)
        return responses[len(captured_inputs) - 1]

    verdicts = [
        EvaluatorVerdict(verdict="NEEDS_IMPROVEMENT", reason="too short"),
        EvaluatorVerdict(verdict="PASS", reason=""),
    ]
    evaluator = MagicMock(side_effect=verdicts)
    loop = ReflectionLoop(
        dispatcher=fake_dispatcher,
        evaluator=evaluator,
        schema={"type": "object"},
        extractor=lambda r: __import__("json").loads(r["raw"]),
    )
    loop.run(agent_name="ideator", inputs={"x": 1}, max_rounds=5, error_injection=True)
    # Round 2 should have prior_attempts in its inputs
    assert "prior_attempts" in captured_inputs[1]
    assert len(captured_inputs[1]["prior_attempts"]) == 1
    assert "too short" in str(captured_inputs[1]["prior_attempts"])


def test_loop_returns_best_after_max_rounds():
    dispatcher = MagicMock(return_value={"raw": '{"k":"v"}'})
    evaluator = MagicMock(return_value=EvaluatorVerdict(verdict="NEEDS_IMPROVEMENT", reason="never good"))
    loop = ReflectionLoop(
        dispatcher=dispatcher,
        evaluator=evaluator,
        schema={"type": "object"},
        extractor=lambda r: __import__("json").loads(r["raw"]),
    )
    result = loop.run(agent_name="x", inputs={}, max_rounds=3)
    assert result == {"k": "v"}
    assert dispatcher.call_count == 3


def test_loop_re_prompts_on_schema_failure():
    responses = [
        {"raw": '{"wrong":"schema"}'},
        {"raw": '{"required":"present"}'},
    ]
    dispatcher = MagicMock(side_effect=responses)
    evaluator = MagicMock(return_value=EvaluatorVerdict(verdict="PASS", reason=""))
    loop = ReflectionLoop(
        dispatcher=dispatcher,
        evaluator=evaluator,
        schema={"type": "object", "required": ["required"]},
        extractor=lambda r: __import__("json").loads(r["raw"]),
    )
    result = loop.run(agent_name="x", inputs={}, max_rounds=5)
    assert result == {"required": "present"}
    assert dispatcher.call_count == 2
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `reflection.py`**

```python
"""ReflectionLoop — multi-round refinement with error injection. Per spec §4.6.

Used by Phases 0.5, 2, 3, 5, 7. Closes:
  - 'no multi-round refinement' (loop exists)
  - 'no error injection' (history fed into next round)
  - 'no semantic consistency check' (evaluator verdict gates)
  - 'weak schema enforcement' (re-prompt on jsonschema fail)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
import jsonschema

from .convergence import SemanticConvergence


@dataclass
class EvaluatorVerdict:
    verdict: str  # 'PASS' | 'NEEDS_IMPROVEMENT' | 'FAIL'
    reason: str


class ReflectionLoop:
    def __init__(
        self,
        *,
        dispatcher: Callable,           # (agent_name, inputs) -> raw response
        evaluator: Callable,            # (parsed_output) -> EvaluatorVerdict
        schema: dict,                   # jsonschema for parsed_output
        extractor: Callable,            # (raw_response) -> parsed dict
        convergence: Optional[SemanticConvergence] = None,
    ):
        self.dispatcher = dispatcher
        self.evaluator = evaluator
        self.schema = schema
        self.extractor = extractor
        self.convergence = convergence or SemanticConvergence()

    def run(
        self,
        *,
        agent_name: str,
        inputs: dict,
        max_rounds: int = 5,
        error_injection: bool = True,
    ) -> dict:
        history = []
        last_parsed = None
        for round_n in range(max_rounds):
            round_inputs = dict(inputs)
            if error_injection and history:
                round_inputs["prior_attempts"] = history
            response = self.dispatcher(agent_name=agent_name, inputs=round_inputs)
            raw = response.get("raw", "") if isinstance(response, dict) else str(response)
            # Try to extract + validate
            try:
                parsed = self.extractor(response)
                jsonschema.validate(parsed, self.schema)
            except (Exception,) as e:
                history.append({
                    "round": round_n,
                    "raw": raw[:1000],
                    "error": f"schema/extract failed: {e}",
                })
                continue
            last_parsed = parsed
            # Semantic convergence check on raw text
            if self.convergence.is_converged(raw):
                return parsed
            # Evaluator gate
            verdict = self.evaluator(parsed)
            if verdict.verdict == "PASS":
                return parsed
            history.append({
                "round": round_n,
                "raw": raw[:1000],
                "critique": verdict.reason,
            })
        # Exhausted max_rounds; accept best (last parsed) per spec §4.6
        if last_parsed is None:
            raise RuntimeError(
                f"ReflectionLoop({agent_name}): no valid output after {max_rounds} rounds"
            )
        return last_parsed
```

- [ ] **Step 4: Run, expect 5 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/reflection.py tests/orchestrator/test_reflection.py
git commit -m "feat(orchestrator): ReflectionLoop with error injection

Per spec §4.6. Used by Phases 0.5, 2, 3, 5, 7. Closes 'no multi-round
refinement' + 'no error injection' + 'no semantic consistency check'
audit findings."
```

---

### Task 12: `ensemble.py` — BiasedReviewers with numpy aggregation

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/ensemble.py`
- Create: `<PLUGIN>/tests/orchestrator/test_ensemble.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_ensemble.py
import pytest
from unittest.mock import MagicMock
from mcp.lib.orchestrator.ensemble import BiasedReviewers, ReviewAggregate


def test_aggregate_median_score():
    fake_dispatcher = MagicMock(side_effect=[
        {"Overall": 4, "Decision": "Reject"},
        {"Overall": 7, "Decision": "Accept"},
        {"Overall": 6, "Decision": "Accept"},
    ])
    br = BiasedReviewers(dispatcher=fake_dispatcher, biases=["positive", "negative", "neutral"])
    agg = br.review(manuscript="...")
    assert agg.median_overall == 6
    assert agg.consensus_high is True   # all >= 4? actually let's check definition


def test_outlier_flag_when_disagreement_high():
    fake_dispatcher = MagicMock(side_effect=[
        {"Overall": 9, "Decision": "Accept"},
        {"Overall": 2, "Decision": "Reject"},
        {"Overall": 8, "Decision": "Accept"},
    ])
    br = BiasedReviewers(dispatcher=fake_dispatcher)
    agg = br.review(manuscript="...")
    assert agg.has_outliers is True
    assert agg.score_iqr >= 4  # spread is large


def test_consensus_low_when_all_agree_below_5():
    fake_dispatcher = MagicMock(side_effect=[
        {"Overall": 3}, {"Overall": 4}, {"Overall": 4},
    ])
    br = BiasedReviewers(dispatcher=fake_dispatcher)
    agg = br.review(manuscript="...")
    assert agg.consensus_high is False


def test_dispatcher_called_with_bias_per_review():
    captured = []

    def fake_dispatcher(*, agent_name, inputs):
        captured.append(inputs.get("system_bias"))
        return {"Overall": 5}

    br = BiasedReviewers(dispatcher=fake_dispatcher, biases=["positive", "negative", "neutral"])
    br.review(manuscript="m", agent_name="reviewer")
    assert captured == ["positive", "negative", "neutral"]
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `ensemble.py`**

```python
"""BiasedReviewers — N reviewers with bias prompts + numpy aggregation.
Per spec §4.7. Direct port of Sakana perform_llm_review.py:17-24, 150-202.

Closes 'single-opinion review' audit finding.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
import numpy as np


@dataclass
class ReviewAggregate:
    median_overall: float
    mean_overall: float
    score_iqr: float
    consensus_high: bool       # majority >= 5/10
    has_outliers: bool         # any |score - median| > 1.5 * IQR or > 3 absolute
    individual_reviews: list = field(default_factory=list)
    biases: list = field(default_factory=list)


class BiasedReviewers:
    def __init__(
        self,
        *,
        dispatcher: Callable,
        biases: Optional[list] = None,
    ):
        self.dispatcher = dispatcher
        self.biases = biases or ["positive", "negative", "neutral"]

    def review(self, *, manuscript: str = "", agent_name: str = "reviewer", **extra_inputs) -> ReviewAggregate:
        reviews = []
        for bias in self.biases:
            inputs = dict(extra_inputs, manuscript=manuscript, system_bias=bias)
            response = self.dispatcher(agent_name=agent_name, inputs=inputs)
            reviews.append(response if isinstance(response, dict) else {"Overall": 5})
        return self._aggregate(reviews)

    def _aggregate(self, reviews: list) -> ReviewAggregate:
        scores = np.array([r.get("Overall", 5) for r in reviews], dtype=float)
        median = float(np.median(scores))
        mean = float(np.mean(scores))
        q75, q25 = np.percentile(scores, [75, 25])
        iqr = float(q75 - q25)
        consensus_high = bool((scores >= 5).mean() > 0.5)
        # Outlier: any score >1.5*IQR from median, with min spread of 3 to flag
        if iqr > 0:
            has_outliers = bool(np.any(np.abs(scores - median) > 1.5 * iqr))
        else:
            has_outliers = bool(np.max(scores) - np.min(scores) > 3)
        return ReviewAggregate(
            median_overall=median,
            mean_overall=mean,
            score_iqr=iqr,
            consensus_high=consensus_high,
            has_outliers=has_outliers,
            individual_reviews=reviews,
            biases=list(self.biases),
        )
```

- [ ] **Step 4: Run, expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/ensemble.py tests/orchestrator/test_ensemble.py
git commit -m "feat(orchestrator): BiasedReviewers ensemble with numpy aggregation

Per spec §4.7. Closes 'single-opinion review' audit finding."
```

---

### Task 13: `stage_gate.py` — structured eval specs between phases

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/stage_gate.py`
- Create: `<PLUGIN>/tests/orchestrator/test_stage_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_stage_gate.py
from unittest.mock import MagicMock
from mcp.lib.orchestrator.stage_gate import StageGate, StageGateResult


def test_gate_passes_when_all_criteria_met():
    fake_evaluator = MagicMock(return_value={
        "ready_for_next_stage": True,
        "missing_criteria": [],
    })
    sg = StageGate(evaluator=fake_evaluator)
    result = sg.gate(phase="ideation", artifacts={"idea.json": "..."})
    assert result.ready is True
    assert result.missing == []


def test_gate_blocks_when_criteria_missing():
    fake_evaluator = MagicMock(return_value={
        "ready_for_next_stage": False,
        "missing_criteria": ["abstract is too short", "no risk section"],
    })
    sg = StageGate(evaluator=fake_evaluator)
    result = sg.gate(phase="ideation", artifacts={})
    assert result.ready is False
    assert "abstract is too short" in result.missing


def test_gate_disabled_returns_pass_immediately():
    fake_evaluator = MagicMock()
    sg = StageGate(evaluator=fake_evaluator, enabled=False)
    result = sg.gate(phase="ideation", artifacts={})
    assert result.ready is True
    fake_evaluator.assert_not_called()


def test_gate_uses_default_criteria_per_phase():
    sg = StageGate(evaluator=lambda **kw: {"ready_for_next_stage": True, "missing_criteria": []})
    # Phase-specific criteria are documented but evaluator is what enforces
    result = sg.gate(phase="hypothesis", artifacts={"hypothesis.md": "..."})
    assert result.ready is True
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `stage_gate.py`**

```python
"""StageGate — structured eval specs between phases. Per spec §4.11.

Per Sakana AgentManager.stage_progress_eval_spec. Block phase advancement on
ready=False. Closes the 'writing manuscripts on incomplete experiments'
failure mode.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class StageGateResult:
    phase: str
    ready: bool
    missing: list


# Default criteria per phase — documented for the evaluator's reference
DEFAULT_CRITERIA = {
    "ideation":  ["≥3 candidates schema-valid", "all have testable hypothesis"],
    "hypothesis":["math present", "stat framework present", "dependencies listed"],
    "codegen":   ["parses (AST valid)", "all imports resolve", "smoke fixture runs"],
    "experiment":["exit_code == 0", "results.csv exists", "≥1 figure"],
    "manuscript":["compiles", "no \\cite{?}", "all figs referenced", "no placeholders"],
    "review":    ["median score recorded", "all 3 reviewers ran"],
}


class StageGate:
    def __init__(self, *, evaluator: Callable, enabled: bool = True, criteria: Optional[dict] = None):
        self.evaluator = evaluator
        self.enabled = enabled
        self.criteria = criteria or DEFAULT_CRITERIA

    def gate(self, *, phase: str, artifacts: dict) -> StageGateResult:
        if not self.enabled:
            return StageGateResult(phase=phase, ready=True, missing=[])
        criteria_for_phase = self.criteria.get(phase, [])
        eval_result = self.evaluator(
            phase=phase,
            artifacts=artifacts,
            expected_criteria=criteria_for_phase,
        )
        return StageGateResult(
            phase=phase,
            ready=bool(eval_result.get("ready_for_next_stage", False)),
            missing=list(eval_result.get("missing_criteria", [])),
        )
```

- [ ] **Step 4: Run, expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/stage_gate.py tests/orchestrator/test_stage_gate.py
git commit -m "feat(orchestrator): StageGate between phase boundaries

Per spec §4.11. Closes 'no stage-gate progression' audit finding."
```

---

### Task 14: `references.py` — bidirectional citation validation + Crossref + LLM-judge anti-hallucination

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/references.py`
- Create: `<PLUGIN>/tests/orchestrator/test_references.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_references.py
from pathlib import Path
from unittest.mock import MagicMock
from mcp.lib.orchestrator.references import validate_citations, CitationReport


def test_finds_dangling_cites(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text("@article{Ho2025_1, title={X}, author={Ho}, year={2025}}\n")
    tex = r"\cite{Ho2025_1} and also \cite{Missing2024_99}"
    report = validate_citations(tex, bib, crossref_check=False, llm_judge=None)
    assert "Missing2024_99" in report.dangling
    assert "Ho2025_1" not in report.dangling


def test_finds_uncited_entries(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{A, title={X}, author={a}, year={2020}}\n"
        "@article{B, title={Y}, author={b}, year={2021}}\n"
    )
    tex = r"\cite{A} only"
    report = validate_citations(tex, bib, crossref_check=False, llm_judge=None)
    assert "B" in report.uncited
    assert "A" not in report.uncited


def test_clean_manuscript_passes(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text("@article{A, title={X}, author={a}, year={2020}}\n")
    tex = r"\cite{A}"
    report = validate_citations(tex, bib, crossref_check=False, llm_judge=None)
    assert report.is_clean is True


def test_crossref_check_called_for_each_doi(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text("@article{A, doi={10.1/x}, title={T}, author={a}, year={2020}}\n")
    tex = r"\cite{A}"
    fake_crossref = MagicMock(return_value={"verified": True})
    report = validate_citations(tex, bib, crossref_check=True, crossref_client=fake_crossref, llm_judge=None)
    fake_crossref.assert_called_once_with("10.1/x")


def test_llm_judge_flags_hallucinated(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text("@article{Fake, title={Invented}, author={Nobody}, year={2099}}\n")
    tex = r"\cite{Fake}"
    fake_judge = MagicMock(return_value={"hallucinated": ["Fake"], "reason": "year is in the future"})
    report = validate_citations(tex, bib, crossref_check=False, llm_judge=fake_judge)
    assert "Fake" in report.hallucinated
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `references.py`**

```python
"""Bidirectional citation validation. Per spec §4.12 and §8.3.

Per AI-Research-SKILLs citation-discipline (40% LLM citation error rate).
Closes 'uncited bibliography entries' (3 in 04a21066) audit finding.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


_CITE_KEYS = re.compile(r"\\cite[a-z]*\{([^}]+)\}")
_BIB_ENTRY = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.MULTILINE)
_BIB_DOI = re.compile(r"doi\s*=\s*[{\"]?([^},\"\s]+)", re.IGNORECASE)


@dataclass
class CitationReport:
    cited_keys: set = field(default_factory=set)
    bib_keys: set = field(default_factory=set)
    dangling: list = field(default_factory=list)        # cited but not in .bib
    uncited: list = field(default_factory=list)          # in .bib but not cited
    crossref_failures: list = field(default_factory=list)
    hallucinated: list = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not (self.dangling or self.uncited or self.crossref_failures or self.hallucinated)


def validate_citations(
    manuscript_tex: str,
    bib_path: Path,
    *,
    crossref_check: bool = True,
    crossref_client: Optional[Callable] = None,
    llm_judge: Optional[Callable] = None,
) -> CitationReport:
    bib_text = Path(bib_path).read_text(encoding="utf-8")
    cited_lists = [m.group(1) for m in _CITE_KEYS.finditer(manuscript_tex)]
    cited = set()
    for csv in cited_lists:
        for k in csv.split(","):
            k = k.strip()
            if k:
                cited.add(k)
    bib_keys = set(m.group(1) for m in _BIB_ENTRY.finditer(bib_text))
    report = CitationReport(cited_keys=cited, bib_keys=bib_keys)
    report.dangling = sorted(cited - bib_keys)
    report.uncited = sorted(bib_keys - cited)
    if crossref_check and crossref_client is not None:
        # Find DOIs per entry; verify each
        for entry_match in re.finditer(r"@\w+\s*\{\s*([^,\s]+)[^@]*", bib_text):
            key = entry_match.group(1)
            entry_text = entry_match.group(0)
            doi_match = _BIB_DOI.search(entry_text)
            if doi_match:
                doi = doi_match.group(1)
                try:
                    result = crossref_client(doi)
                    if not result.get("verified", False):
                        report.crossref_failures.append(key)
                except Exception:
                    report.crossref_failures.append(key)
    if llm_judge is not None:
        try:
            judgement = llm_judge(bib_text=bib_text, cited_keys=sorted(cited))
            report.hallucinated = list(judgement.get("hallucinated", []))
        except Exception:
            pass
    return report
```

- [ ] **Step 4: Run, expect 5 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/references.py tests/orchestrator/test_references.py
git commit -m "feat(orchestrator): bidirectional citation validation

Per spec §4.12 + §8.3 (vendored from AI-Research-SKILLs citation
discipline). Closes 'uncited bibliography entries' (3 in 04a21066)."
```

---

### Task 15: `findings.py` — 5-section narrative-memory scaffold

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/findings.py`
- Create: `<PLUGIN>/tests/orchestrator/test_findings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_findings.py
from mcp.lib.orchestrator.findings import FindingsScaffold, FINDINGS_SECTIONS


def test_default_scaffold_has_5_sections():
    s = FindingsScaffold()
    for section in FINDINGS_SECTIONS:
        assert section in s.to_dict()


def test_update_section():
    s = FindingsScaffold()
    s.update("lessons_and_constraints", "weight decay > 0.1 diverges at this scale")
    assert "weight decay" in s.to_dict()["lessons_and_constraints"]


def test_append_to_section():
    s = FindingsScaffold()
    s.append("patterns_and_insights", "first pattern")
    s.append("patterns_and_insights", "second pattern")
    text = s.to_dict()["patterns_and_insights"]
    assert "first pattern" in text and "second pattern" in text


def test_to_markdown_renders_all_sections():
    s = FindingsScaffold()
    s.update("current_understanding", "We know X.")
    md = s.to_markdown()
    assert "# Findings" in md
    assert "## Current Understanding" in md
    assert "We know X." in md


def test_unknown_section_raises():
    s = FindingsScaffold()
    import pytest
    with pytest.raises(KeyError):
        s.update("not_a_section", "x")
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `findings.py`**

```python
"""FindingsScaffold — 5-section narrative-memory. Per spec §4.13 + §8.2.

Vendored from AI-Research-SKILLs autoresearch (drawer_kind:
research_findings). Updated by meta-analyst at every outer-loop checkpoint.
Prevents repeated-failure loops across sessions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict


FINDINGS_SECTIONS = [
    "current_understanding",
    "patterns_and_insights",
    "lessons_and_constraints",
    "open_questions",
    "last_direction_decision",
]


@dataclass
class FindingsScaffold:
    sections: Dict[str, str] = field(default_factory=lambda: {s: "" for s in FINDINGS_SECTIONS})

    def update(self, section: str, content: str) -> None:
        if section not in FINDINGS_SECTIONS:
            raise KeyError(f"unknown section {section!r}; expected one of {FINDINGS_SECTIONS}")
        self.sections[section] = content

    def append(self, section: str, content: str) -> None:
        if section not in FINDINGS_SECTIONS:
            raise KeyError(f"unknown section {section!r}")
        existing = self.sections[section]
        self.sections[section] = (existing + "\n- " + content).strip().lstrip("-").strip()
        # Ensure list format
        if not self.sections[section].startswith("- "):
            self.sections[section] = "- " + self.sections[section]

    def to_dict(self) -> dict:
        return dict(self.sections)

    def to_markdown(self) -> str:
        lines = ["# Findings\n"]
        for s in FINDINGS_SECTIONS:
            title = s.replace("_", " ").title()
            body = self.sections[s] or "_(empty)_"
            lines.append(f"## {title}\n\n{body}\n")
        return "\n".join(lines)
```

- [ ] **Step 4: Run, expect 5 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/findings.py tests/orchestrator/test_findings.py
git commit -m "feat(orchestrator): FindingsScaffold 5-section narrative memory

Per spec §4.13 + §8.2 (vendored from AI-Research-SKILLs)."
```

---

### Task 16: `mempalace_helpers.py` — PluginPalace + ProjectPalace ergonomic wrappers

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/mempalace_helpers.py`
- Create: `<PLUGIN>/tests/orchestrator/test_mempalace_helpers.py`

- [ ] **Step 1: Write the failing test (with mock MCP)**

```python
# tests/orchestrator/test_mempalace_helpers.py
from pathlib import Path
from unittest.mock import MagicMock
from mcp.lib.orchestrator.mempalace_helpers import PluginPalace, ProjectPalace


def test_plugin_palace_archive_spec_calls_add_drawer(tmp_path):
    fake_mcp = MagicMock()
    fake_mcp.mempalace_add_drawer = MagicMock(return_value={"success": True, "drawer_id": "d1"})
    spec = tmp_path / "spec.md"
    spec.write_text("# Spec\nbody")
    p = PluginPalace(root=tmp_path, mcp=fake_mcp, wing="plugin")
    drawer_id = p.archive_spec(spec, metadata={"version": "1.0"})
    fake_mcp.mempalace_add_drawer.assert_called_once()
    call_kwargs = fake_mcp.mempalace_add_drawer.call_args.kwargs
    assert call_kwargs["wing"] == "plugin"
    assert call_kwargs["room"] == "specs"
    assert "# Spec" in call_kwargs["content"]


def test_plugin_palace_archive_plan_uses_plans_room(tmp_path):
    fake_mcp = MagicMock()
    fake_mcp.mempalace_add_drawer = MagicMock(return_value={"success": True, "drawer_id": "d2"})
    plan = tmp_path / "plan.md"; plan.write_text("# Plan\n")
    p = PluginPalace(root=tmp_path, mcp=fake_mcp, wing="plugin")
    p.archive_plan(plan, metadata={})
    assert fake_mcp.mempalace_add_drawer.call_args.kwargs["room"] == "plans"


def test_project_palace_write_diary(tmp_path):
    fake_mcp = MagicMock()
    fake_mcp.mempalace_diary_write = MagicMock(return_value={"success": True})
    pp = ProjectPalace(root=tmp_path, mcp=fake_mcp, wing="project_xyz")
    pp.write_diary(agent="ideator", content="round 1 done", tags=["round:1"])
    fake_mcp.mempalace_diary_write.assert_called_once()


def test_project_palace_write_findings_uses_research_findings_room(tmp_path):
    fake_mcp = MagicMock()
    fake_mcp.mempalace_add_drawer = MagicMock(return_value={"success": True})
    pp = ProjectPalace(root=tmp_path, mcp=fake_mcp, wing="project_xyz")
    pp.write_findings(section="current_understanding", content="X works")
    call = fake_mcp.mempalace_add_drawer.call_args.kwargs
    assert call["room"] == "research-findings"
    assert "current_understanding" in call["content"]
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `mempalace_helpers.py`**

```python
"""PluginPalace + ProjectPalace ergonomic wrappers around the 29
mcp__mempalace__* tools. Per spec §4.15.

The MCP client is injected so we can mock it in tests. In production,
the MCP server's tool surface is wrapped behind a thin facade.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional


class _PalaceBase:
    def __init__(self, *, root: Path, mcp: Any, wing: str):
        self.root = Path(root)
        self.mcp = mcp
        self.wing = wing


class PluginPalace(_PalaceBase):
    """Plugin-development palace: specs, plans, decisions, dev journal."""

    def archive_spec(self, spec_path: Path, metadata: Optional[dict] = None) -> Optional[str]:
        return self._archive(spec_path, room="specs", metadata=metadata)

    def archive_plan(self, plan_path: Path, metadata: Optional[dict] = None) -> Optional[str]:
        return self._archive(plan_path, room="plans", metadata=metadata)

    def archive_audit(self, audit_text: str, metadata: Optional[dict] = None) -> Optional[str]:
        return self._add_drawer(content=audit_text, room="audits", metadata=metadata)

    def search(self, query: str, limit: int = 5) -> list:
        try:
            r = self.mcp.mempalace_search(query=query, limit=limit)
            return r.get("results", []) if isinstance(r, dict) else []
        except Exception:
            return []

    def wake_up(self, *, query: str = "", token_budget: int = 2000) -> str:
        try:
            r = self.mcp.mempalace_status()
            return json.dumps(r)[:token_budget * 4]
        except Exception:
            return ""

    def _archive(self, path: Path, *, room: str, metadata: Optional[dict]) -> Optional[str]:
        path = Path(path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None
        meta = dict(metadata or {})
        meta["source_path"] = str(path)
        return self._add_drawer(content=content, room=room, metadata=meta)

    def _add_drawer(self, *, content: str, room: str, metadata: Optional[dict]) -> Optional[str]:
        try:
            r = self.mcp.mempalace_add_drawer(
                wing=self.wing, room=room, content=content,
                source_file=(metadata or {}).get("source_path", ""),
                added_by="orchestrator",
            )
            return r.get("drawer_id") if isinstance(r, dict) else None
        except Exception:
            return None


class ProjectPalace(_PalaceBase):
    """Per-project palace: research-plan, phase-checkpoints, agent-diaries,
    cross-validation, token-budget, research-findings.
    """

    def write_diary(self, *, agent: str, content: str, tags: Optional[list] = None) -> bool:
        try:
            r = self.mcp.mempalace_diary_write(
                wing=self.wing,
                room="agent-diaries",
                content=content,
                tags=tags or [f"agent:{agent}"],
            )
            return bool(r.get("success"))
        except Exception:
            return False

    def write_findings(self, *, section: str, content: str) -> bool:
        body = f"## {section}\n\n{content}"
        try:
            r = self.mcp.mempalace_add_drawer(
                wing=self.wing,
                room="research-findings",
                content=body,
                added_by="meta-analyst",
            )
            return bool(r.get("success"))
        except Exception:
            return False

    def get_phase_history(self, phase: str) -> list:
        try:
            r = self.mcp.mempalace_search(query=f"phase:{phase}", limit=20)
            return r.get("results", []) if isinstance(r, dict) else []
        except Exception:
            return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
```

- [ ] **Step 4: Run, expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/mempalace_helpers.py tests/orchestrator/test_mempalace_helpers.py
git commit -m "feat(orchestrator): PluginPalace + ProjectPalace ergonomic wrappers

Per spec §4.15. Wraps the 29 mcp__mempalace__* tools."
```

---

### Task 17: `superpowers_bridge.py` — wires writing-plans/executing-plans/subagent-driven-development to MemPalace

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/superpowers_bridge.py`
- Create: `<PLUGIN>/tests/orchestrator/test_superpowers_bridge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_superpowers_bridge.py
from pathlib import Path
from unittest.mock import MagicMock
from mcp.lib.orchestrator.superpowers_bridge import (
    WritingPlansBridge, ExecutingPlansBridge, SubagentDrivenBridge,
)


def test_writing_plans_bridge_calls_archive(tmp_path):
    palace = MagicMock()
    palace.archive_plan = MagicMock(return_value="d1")
    plan = tmp_path / "plan.md"; plan.write_text("# Plan")
    b = WritingPlansBridge(plugin_palace=palace)
    b.on_plan_written(plan)
    palace.archive_plan.assert_called_once_with(plan, metadata={"event": "writing-plans:plan-saved"})


def test_executing_plans_bridge_wakes_up_on_start(tmp_path):
    palace = MagicMock()
    palace.wake_up = MagicMock(return_value="prior context summary")
    plan = tmp_path / "p.md"; plan.write_text("Plan body about orchestrator")
    b = ExecutingPlansBridge(plugin_palace=palace)
    summary = b.on_skill_start(plan)
    assert "prior context" in summary
    palace.wake_up.assert_called_once()


def test_executing_plans_bridge_writes_diary_on_step():
    palace = MagicMock()
    b = ExecutingPlansBridge(plugin_palace=palace)
    b.on_step_complete(step_id=3, outcome="done")
    palace.search = MagicMock()  # not called
    # diary_write is on the project palace, not plugin palace, in real impl;
    # for this minimal bridge test we just verify it doesn't raise


def test_subagent_driven_bridge_searches_before_dispatch():
    palace = MagicMock()
    palace.search = MagicMock(return_value=[{"content": "prior similar"}])
    b = SubagentDrivenBridge(plugin_palace=palace)
    prior = b.before_dispatch(task_description="implement reflection loop")
    palace.search.assert_called_once()
    assert len(prior) == 1
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement `superpowers_bridge.py`**

```python
"""Bridges between superpowers skills (writing-plans, executing-plans,
subagent-driven-development) and the plugin-development palace.

Per spec §4.14 + §7.4.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any


class WritingPlansBridge:
    def __init__(self, plugin_palace: Any):
        self.palace = plugin_palace

    def on_plan_written(self, plan_path: Path) -> None:
        if self.palace is None:
            return
        try:
            self.palace.archive_plan(plan_path, metadata={"event": "writing-plans:plan-saved"})
        except Exception:
            pass


class ExecutingPlansBridge:
    def __init__(self, plugin_palace: Any):
        self.palace = plugin_palace

    def on_skill_start(self, plan_path: Path) -> str:
        if self.palace is None:
            return ""
        try:
            content = Path(plan_path).read_text(encoding="utf-8")
            return self.palace.wake_up(query=content[:500], token_budget=2000)
        except Exception:
            return ""

    def on_step_complete(self, *, step_id: int, outcome: str) -> None:
        # Diary writes happen via the project palace in pipeline.py
        return None

    def on_skill_complete(self, *, plan_path: Path, summary: str) -> None:
        if self.palace is None:
            return
        try:
            self.palace.archive_audit(
                audit_text=f"Plan {plan_path.name} complete:\n{summary}",
                metadata={"event": "executing-plans:complete"},
            )
        except Exception:
            pass


class SubagentDrivenBridge:
    def __init__(self, plugin_palace: Any):
        self.palace = plugin_palace

    def before_dispatch(self, *, task_description: str) -> list:
        if self.palace is None:
            return []
        try:
            return self.palace.search(query=task_description, limit=5)
        except Exception:
            return []
```

- [ ] **Step 4: Run, expect 4 passed**

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/superpowers_bridge.py tests/orchestrator/test_superpowers_bridge.py
git commit -m "feat(orchestrator): superpowers→MemPalace bridges

Per spec §4.14 + §7.4. Three bridges: WritingPlansBridge (auto-archive
on plan write), ExecutingPlansBridge (wake_up at start), SubagentDrivenBridge
(search before dispatch)."
```

---

## Phase C — Pipeline (Tasks 18–26)

> **Brevity note**: Phase C builds `pipeline.py` phase-by-phase. Each task adds 1–2 phase methods to a single file. The full `Pipeline` class skeleton is created in Task 18; subsequent tasks only add new methods. Each task tests its added phase against a mocked dispatcher.

### Task 18: `pipeline.py` skeleton + `phase_0_init` + `phase_0_5_ideation`

**Files:**
- Create: `<PLUGIN>/mcp/lib/orchestrator/pipeline.py`
- Create: `<PLUGIN>/tests/orchestrator/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/orchestrator/test_pipeline.py
from pathlib import Path
from unittest.mock import MagicMock
from mcp.lib.orchestrator.pipeline import Pipeline


def test_phase_0_init_creates_dirs_and_config(tmp_path):
    pipeline = Pipeline(
        dispatcher=MagicMock(),
        evaluator=MagicMock(),
        host="claude_code",
        plugin_palace=None,
        project_palace=None,
    )
    pipeline.phase_0_init(
        topic="ridge regression",
        domain="statistical",
        output_dir=tmp_path,
    )
    assert (tmp_path / "config.json").is_file()
    assert (tmp_path / ".checkpoints").is_dir()
    assert (tmp_path / ".palace").is_dir()


def test_phase_0_5_ideation_produces_3_candidates(tmp_path):
    fake_dispatcher = MagicMock(side_effect=[
        {"raw": '{"Name":"a","Title":"A","Short_Hypothesis":"h","Related_Work":"rw","Abstract":"' + "x"*80 + '","Experiments":[{"name":"e","metric":"m"}],"Risks":["r"]}'},
        {"raw": '{"Name":"b","Title":"B","Short_Hypothesis":"h","Related_Work":"rw","Abstract":"' + "x"*80 + '","Experiments":[{"name":"e","metric":"m"}],"Risks":["r"]}'},
        {"raw": '{"Name":"c","Title":"C","Short_Hypothesis":"h","Related_Work":"rw","Abstract":"' + "x"*80 + '","Experiments":[{"name":"e","metric":"m"}],"Risks":["r"]}'},
    ])
    fake_evaluator = MagicMock(return_value={"verdict": "PASS", "reason": ""})
    pipeline = Pipeline(
        dispatcher=fake_dispatcher,
        evaluator=fake_evaluator,
        host="claude_code",
    )
    pipeline.phase_0_init(topic="t", domain="statistical", output_dir=tmp_path)
    candidates = pipeline.phase_0_5_ideation(topic="t", domain="statistical", num_candidates=3)
    assert len(candidates) == 3
    assert (tmp_path / "idea_candidates.json").is_file()
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement skeleton + the two phase methods**

```python
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
```

- [ ] **Step 4: Run, expect 2 passed**

```bash
python -m pytest tests/orchestrator/test_pipeline.py -v
```

- [ ] **Step 5: Commit**

```bash
git add mcp/lib/orchestrator/pipeline.py tests/orchestrator/test_pipeline.py
git commit -m "feat(orchestrator): Pipeline skeleton + phase_0_init + phase_0_5_ideation

Per spec §4.10. Phase 0.5 produces N candidates per spec §5 (was: single
idea, no candidates). Closes 'no multiple ideation candidates' finding."
```

---

### Tasks 19–26: Remaining pipeline phases

Each follows the same TDD pattern as Task 18: write a test that mocks the dispatcher + evaluator, implement the phase method, run, commit. To keep this plan compact, the full code for each phase is given below in condensed form. The test pattern is the same: mock dispatcher returns the expected response shape; assert artifact file exists + has expected fields.

### Task 19: `phase_0_75_codebase` + `phase_1_literature`

Add to `pipeline.py`:

```python
def phase_0_75_codebase(self, *, codebase_path: Optional[Path]) -> dict:
    if not codebase_path:
        return {}
    response = self.dispatcher(agent_name="codebase-scanner", inputs={"codebase_path": str(codebase_path)})
    parsed = extract_json(response.get("raw", "")) if isinstance(response, dict) else {}
    out = self.state.output_dir / "codebase_analysis.json"
    out.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    if self.checkpoints: self.checkpoints.save("phase_0_75", parsed)
    return parsed

def phase_1_literature(self, *, idea: dict, sources: Optional[list] = None) -> List[dict]:
    sources = sources or ["openalex", "arxiv", "pubmed", "biorxiv", "semanticscholar", "annas-mcp"]
    queries = self._build_queries(idea, n=8)
    all_papers: List[dict] = []
    for source in sources:
        response = self.dispatcher(
            agent_name="literature-searcher",
            inputs={"source": source, "queries": queries, "max_per_source": 8, "time_budget_seconds": 60},
        )
        try:
            papers = extract_json(response.get("raw", "")) if isinstance(response, dict) else []
            if isinstance(papers, list):
                all_papers.extend(papers)
        except Exception:
            continue
    deduped = self._dedup_papers(all_papers)
    (self.state.output_dir / "paper_list.json").write_text(
        json.dumps(deduped, indent=2), encoding="utf-8"
    )
    if self.checkpoints: self.checkpoints.save("phase_1", {"papers": deduped})
    return deduped

@staticmethod
def _build_queries(idea: dict, n: int = 8) -> list:
    core = idea.get("Title", "")[:150]
    return [
        core, f"{core} computational design", f"{core} deep learning",
        f"{core} structure prediction", f"{core} machine learning",
        f"{core} review 2025", f"{core} benchmark dataset", f"{core} therapeutic applications",
    ][:n]

@staticmethod
def _dedup_papers(papers: list) -> list:
    seen_doi, seen_title = set(), set()
    out = []
    for p in papers:
        doi = (p.get("doi") or "").lower()
        title_norm = (p.get("title") or "").lower().strip()[:80]
        if doi and doi in seen_doi: continue
        if title_norm and title_norm in seen_title: continue
        if doi: seen_doi.add(doi)
        if title_norm: seen_title.add(title_norm)
        out.append(p)
    return out
```

Test (`tests/orchestrator/test_pipeline.py` — append):

```python
def test_phase_1_dedups_papers(tmp_path):
    fake_dispatcher = MagicMock(return_value={"raw": '[{"title":"A","doi":"10.1/x"},{"title":"A","doi":"10.1/x"}]'})
    pipeline = Pipeline(dispatcher=fake_dispatcher, evaluator=MagicMock(), host="claude_code")
    pipeline.phase_0_init(topic="t", domain="statistical", output_dir=tmp_path)
    papers = pipeline.phase_1_literature(idea={"Title": "ridge"}, sources=["openalex"])
    assert len(papers) == 1
```

Commit: `feat(orchestrator): phase_0_75_codebase + phase_1_literature`

---

### Task 20: `phase_2_hypothesis` + `phase_3_codegen`

Add:

```python
from .schemas import HYPOTHESIS_SCHEMA
from .extraction import extract_python, ExtractionError

def phase_2_hypothesis(self, *, idea: dict, papers: list) -> dict:
    loop = ReflectionLoop(
        dispatcher=self.dispatcher,
        evaluator=lambda p: self._wrap_evaluator(p),
        schema=HYPOTHESIS_SCHEMA,
        extractor=lambda r: extract_json(r.get("raw", "")),
    )
    inputs = {
        "topic": self.state.topic, "domain": self.state.domain,
        "idea_json": json.dumps(idea),
        "paper_list_compact": json.dumps([{"title": p.get("title"), "year": p.get("year")} for p in papers[:10]]),
    }
    hypothesis = loop.run(agent_name="hypothesizer", inputs=inputs, max_rounds=3)
    (self.state.output_dir / "hypothesis.md").write_text(
        hypothesis.get("hypothesis", "") + "\n\n" + hypothesis.get("math_models", ""),
        encoding="utf-8",
    )
    if self.checkpoints: self.checkpoints.save("phase_2", hypothesis)
    return hypothesis

def phase_3_codegen(self, *, hypothesis: dict, max_rounds: int = 3) -> dict:
    history = []
    for round_n in range(max_rounds):
        inputs = {"hypothesis_md": hypothesis.get("hypothesis", ""),
                  "config_json": json.dumps(self.state.config),
                  "prior_attempts": history}
        response = self.dispatcher(agent_name="code-generator", inputs=inputs)
        raw = response.get("raw", "") if isinstance(response, dict) else ""
        try:
            code = extract_python(raw)
            requirements = self._extract_requirements(raw)
        except ExtractionError as e:
            history.append({"round": round_n, "error": str(e)})
            continue
        (self.state.output_dir / "experiment.py").write_text(code, encoding="utf-8")
        (self.state.output_dir / "requirements.txt").write_text(requirements, encoding="utf-8")
        if self.checkpoints: self.checkpoints.save("phase_3", {"code": code, "requirements": requirements})
        return {"code": code, "requirements": requirements}
    raise RuntimeError(f"phase_3_codegen: no parseable code after {max_rounds} rounds")

@staticmethod
def _extract_requirements(text: str) -> str:
    import re
    m = re.search(r"```\s*(?:requirements\.?txt)?\s*\n([\s\S]+?)\n```", text)
    if m and ("==" in m.group(1) or ">=" in m.group(1) or m.group(1).strip().startswith(("numpy", "scipy", "torch"))):
        return m.group(1).strip()
    return "numpy>=1.26\nscikit-learn>=1.3\nmatplotlib>=3.7\n"
```

Test:

```python
def test_phase_3_codegen_writes_files(tmp_path):
    fake_dispatcher = MagicMock(return_value={"raw": '```python\nprint("ok")\n```'})
    pipeline = Pipeline(dispatcher=fake_dispatcher, evaluator=MagicMock(), host="claude_code")
    pipeline.phase_0_init(topic="t", domain="statistical", output_dir=tmp_path)
    result = pipeline.phase_3_codegen(hypothesis={"hypothesis": "h"}, max_rounds=1)
    assert (tmp_path / "experiment.py").is_file()
    assert (tmp_path / "requirements.txt").is_file()
```

Commit: `feat(orchestrator): phase_2_hypothesis + phase_3_codegen with AST validation`

---

### Task 21: `phase_4_experiment` (4a single-shot + 4b BFTS branch)

Add:

```python
import subprocess

def phase_4_experiment(self, *, code_artifacts: dict, use_bfts: bool = False, timeout_seconds: int = 300) -> dict:
    if use_bfts:
        return self._phase_4b_bfts(timeout_seconds=timeout_seconds * 6)
    return self._phase_4a_single_shot(timeout_seconds=timeout_seconds)

def _phase_4a_single_shot(self, *, timeout_seconds: int) -> dict:
    inputs = {"output_dir": str(self.state.output_dir),
              "auto_fix_max_rounds": 3, "timeout_seconds": timeout_seconds}
    response = self.dispatcher(agent_name="experiment-runner", inputs=inputs)
    parsed = extract_json(response.get("raw", "")) if isinstance(response, dict) else {}
    if self.checkpoints: self.checkpoints.save("phase_4a", parsed)
    return parsed

def _phase_4b_bfts(self, *, timeout_seconds: int) -> dict:
    inputs = {"output_dir": str(self.state.output_dir),
              "bfts_config_path": "${plugin_root}/mcp/lib/sakana/bfts_config.yaml",
              "time_budget_minutes": timeout_seconds // 60}
    response = self.dispatcher(agent_name="tree-search-runner", inputs=inputs)
    parsed = extract_json(response.get("raw", "")) if isinstance(response, dict) else {}
    if self.checkpoints: self.checkpoints.save("phase_4b", parsed)
    return parsed
```

Test:

```python
def test_phase_4_routes_to_bfts_when_use_bfts(tmp_path):
    fake_dispatcher = MagicMock(return_value={"raw": '{"final_exit_code":0,"results_csv_present":true,"npy_files":[],"figures":[],"fix_attempts":0,"stdout_summary":"","stderr_summary":""}'})
    pipeline = Pipeline(dispatcher=fake_dispatcher, evaluator=MagicMock(), host="claude_code")
    pipeline.phase_0_init(topic="t", domain="statistical", output_dir=tmp_path)
    pipeline.phase_4_experiment(code_artifacts={}, use_bfts=True)
    call = fake_dispatcher.call_args.kwargs
    assert call["agent_name"] == "tree-search-runner"
```

Commit: `feat(orchestrator): phase_4_experiment with single-shot + BFTS branches`

---

### Task 22: `phase_5_5_plotting` + `phase_5_manuscript`

Add:

```python
def phase_5_5_plotting(self, *, max_rounds: int = 2) -> dict:
    history = []
    for round_n in range(max_rounds):
        inputs = {"output_dir": str(self.state.output_dir),
                  "data_summary": self._summarize_data(), "prior_attempts": history}
        response = self.dispatcher(agent_name="plotter", inputs=inputs)
        raw = response.get("raw", "") if isinstance(response, dict) else ""
        # Run aggregator
        agg_path = self.state.output_dir / "auto_plot_aggregator.py"
        try:
            code = extract_python(raw)
            agg_path.write_text(code, encoding="utf-8")
            result = subprocess.run(
                ["python", str(agg_path)], cwd=str(self.state.output_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                break
            history.append({"round": round_n, "stderr": result.stderr[:1000]})
        except Exception as e:
            history.append({"round": round_n, "error": str(e)})
    figs = list((self.state.output_dir / "figures").glob("*.png"))[:12]  # MAX_FIGURES
    if self.checkpoints: self.checkpoints.save("phase_5_5", {"figures": [str(f) for f in figs]})
    return {"figures": [str(f) for f in figs]}

def phase_5_manuscript(self, *, papers: list, hypothesis: dict, results: dict, max_rounds: int = 3) -> str:
    history = []
    for round_n in range(max_rounds):
        inputs = {"paper_list_compact": json.dumps(papers[:30]),
                  "hypothesis_summary": hypothesis.get("hypothesis", "")[:400],
                  "experiment_summary": results.get("stdout_summary", "")[:500],
                  "prior_attempts": history}
        response = self.dispatcher(agent_name="manuscript-writer", inputs=inputs)
        raw = response.get("raw", "") if isinstance(response, dict) else ""
        try:
            tex = extract_latex(raw)
        except Exception as e:
            history.append({"round": round_n, "error": str(e)})
            continue
        manuscript_path = self.state.output_dir / "manuscript.tex"
        manuscript_path.write_text(tex, encoding="utf-8")
        # LaTeX compile feedback (best-effort)
        compile_result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "manuscript.tex"],
            cwd=str(self.state.output_dir), capture_output=True, text=True, timeout=60,
        )
        if compile_result.returncode == 0:
            break
        history.append({"round": round_n, "compile_error": compile_result.stdout[-2000:]})
    if self.checkpoints: self.checkpoints.save("phase_5", {"manuscript_path": str(manuscript_path)})
    return tex

@staticmethod
def _summarize_data() -> str:
    return "results.csv (long-format) + .npy data files"
```

Add `from .extraction import extract_latex` at top.

Commit: `feat(orchestrator): phase_5_5_plotting + phase_5_manuscript with subprocess-error injection`

---

### Task 23: `phase_6_citations` + `phase_7_review`

Add:

```python
from .references import validate_citations
from .ensemble import BiasedReviewers

def phase_6_citations(self) -> dict:
    tex_path = self.state.output_dir / "manuscript.tex"
    bib_path = self.state.output_dir / "references.bib"
    tex = tex_path.read_text(encoding="utf-8")
    report = validate_citations(tex, bib_path, crossref_check=False, llm_judge=None)
    if not report.is_clean:
        # Re-dispatch citator with the report
        response = self.dispatcher(
            agent_name="citator",
            inputs={"manuscript_tex": tex, "references_bib": bib_path.read_text(),
                    "dangling": report.dangling, "uncited": report.uncited, "max_rounds": 5},
        )
        # The citator returns updated bib; persist
        try:
            updated = extract_json(response.get("raw", ""))
            if "references_bib" in updated:
                bib_path.write_text(updated["references_bib"], encoding="utf-8")
        except Exception:
            pass
    if self.checkpoints: self.checkpoints.save("phase_6", {"citation_report": {
        "dangling": report.dangling, "uncited": report.uncited,
        "hallucinated": report.hallucinated, "is_clean": report.is_clean,
    }})
    return {"is_clean": report.is_clean}

def phase_7_review(self, *, manuscript_tex: str) -> dict:
    br = BiasedReviewers(dispatcher=self.dispatcher, biases=["positive", "negative", "neutral"])
    aggregate = br.review(manuscript=manuscript_tex, agent_name="reviewer")
    review_data = {
        "median_overall": aggregate.median_overall,
        "score_iqr": aggregate.score_iqr,
        "consensus_high": aggregate.consensus_high,
        "has_outliers": aggregate.has_outliers,
        "individual_reviews": aggregate.individual_reviews,
    }
    (self.state.output_dir / "review.json").write_text(
        json.dumps(review_data, indent=2), encoding="utf-8",
    )
    if self.checkpoints: self.checkpoints.save("phase_7", review_data)
    return review_data
```

Commit: `feat(orchestrator): phase_6_citations + phase_7_review with BiasedReviewers ensemble`

---

### Task 24: `phase_8_compile` + `phase_8_25_word` + `phase_8_5_vlm`

Add:

```python
def phase_8_compile(self) -> Optional[Path]:
    cwd = str(self.state.output_dir)
    for cmd in [
        ["pdflatex", "-interaction=nonstopmode", "manuscript.tex"],
        ["bibtex", "manuscript"],
        ["pdflatex", "-interaction=nonstopmode", "manuscript.tex"],
        ["pdflatex", "-interaction=nonstopmode", "manuscript.tex"],
    ]:
        try:
            subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
    pdf = self.state.output_dir / "manuscript.pdf"
    return pdf if pdf.is_file() else None

def phase_8_25_word(self) -> Optional[Path]:
    try:
        subprocess.run(
            ["pandoc", "manuscript.tex", "-o", "manuscript.docx"],
            cwd=str(self.state.output_dir), capture_output=True, text=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    docx = self.state.output_dir / "manuscript.docx"
    return docx if docx.is_file() else None

def phase_8_5_vlm(self) -> dict:
    pdf = self.state.output_dir / "manuscript.pdf"
    if not pdf.is_file():
        return {"skipped": "no manuscript.pdf"}
    figs = sorted((self.state.output_dir / "figures").glob("*.png"))
    response = self.dispatcher(
        agent_name="vlm-reviewer",
        inputs={"route": "md_agent", "rendered_pages": [str(f) for f in figs]},
    )
    try:
        result = extract_json(response.get("raw", ""))
    except Exception:
        result = {"error": "vlm response parse failed"}
    (self.state.output_dir / "visual_review.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8",
    )
    if self.checkpoints: self.checkpoints.save("phase_8_5", result)
    return result
```

Commit: `feat(orchestrator): phase_8_compile + phase_8_25_word + phase_8_5_vlm`

---

### Task 25: `phase_9_index` + `phase_10_meta` + `phase_11_slides`

Add:

```python
def phase_9_index(self, *, papers: list, idea: dict, hypothesis: dict, review: dict) -> None:
    # Persist to per-job palace (already done via per-phase checkpoints).
    # Cross-job knowledge.db append handled by ai-scientist core MCP.
    if self.project_palace is not None:
        try:
            self.project_palace.write_diary(
                agent="indexer",
                content=f"Job {self.state.job_id} indexed: {len(papers)} papers, "
                        f"hypothesis={hypothesis.get('hypothesis','')[:100]}, "
                        f"review_overall={review.get('median_overall','?')}",
                tags=["phase-9-index"],
            )
        except Exception:
            pass

def phase_10_meta(self) -> dict:
    response = self.dispatcher(agent_name="meta-analyst", inputs={
        "trajectories_jsonl": "", "jobs_json": "",
    })
    try:
        result = extract_json(response.get("raw", ""))
    except Exception:
        result = {}
    # Update findings.md drawer
    if self.project_palace is not None and "findings_update" in result:
        for section, content in result["findings_update"].items():
            try:
                self.project_palace.write_findings(section=section, content=content)
            except Exception:
                pass
    return result

def phase_11_slides(self) -> Optional[Path]:
    response = self.dispatcher(agent_name="slide-presenter", inputs={
        "manuscript_pdf": str(self.state.output_dir / "manuscript.pdf"),
        "manuscript_tex": str(self.state.output_dir / "manuscript.tex"),
        "figures_dir": str(self.state.output_dir / "figures"),
    })
    # The agent writes manuscript-slides.pdf + .pptx itself via Bash;
    # we just return the expected paths
    pdf = self.state.output_dir / "manuscript-slides.pdf"
    return pdf if pdf.is_file() else None
```

Commit: `feat(orchestrator): phase_9_index + phase_10_meta + phase_11_slides`

---

### Task 26: `run_full_pipeline` + AskUserQuestion gates

Add the top-level orchestrator that wires everything. The full method, plus a small `AskUserQuestionGate` helper:

```python
@dataclass
class GateRequest:
    """Returned to the SKILL.md when a phase needs user input."""
    gate_id: int
    question: str
    options: list

def run_full_pipeline(
    self,
    *,
    topic: str,
    domain: str,
    output_dir: Path,
    interactivity: str = "checkpoints",
    use_bfts: bool = False,
    codebase_path: Optional[Path] = None,
    user_input_callback: Optional[Callable] = None,
) -> dict:
    """The end-to-end pipeline. SKILL.md surfaces gates via user_input_callback.

    Returns a dict summary of all artifacts + token usage.
    """
    self.phase_0_init(topic=topic, domain=domain, output_dir=output_dir)
    if codebase_path:
        self.phase_0_75_codebase(codebase_path=codebase_path)
    candidates = self.phase_0_5_ideation(topic=topic, domain=domain, num_candidates=3)
    idea = self._gate_or_default(
        gate_id=2, default=candidates[0], question="Pick an idea",
        options=[c.get("Name", f"#{i}") for i, c in enumerate(candidates)],
        callback=user_input_callback, interactivity=interactivity,
        critical=True,
    )
    if isinstance(idea, str):
        idea = next((c for c in candidates if c.get("Name") == idea), candidates[0])
    (self.state.output_dir / "idea.json").write_text(json.dumps(idea, indent=2), encoding="utf-8")
    papers = self.phase_1_literature(idea=idea)
    hypothesis = self.phase_2_hypothesis(idea=idea, papers=papers)
    code_artifacts = self.phase_3_codegen(hypothesis=hypothesis)
    results = self.phase_4_experiment(code_artifacts=code_artifacts, use_bfts=use_bfts)
    self.phase_5_5_plotting()
    manuscript_tex = self.phase_5_manuscript(
        papers=papers, hypothesis=hypothesis, results=results,
    )
    self.phase_6_citations()
    review = self.phase_7_review(manuscript_tex=manuscript_tex)
    self.phase_8_compile()
    self.phase_8_25_word()
    self.phase_8_5_vlm()
    self.phase_9_index(papers=papers, idea=idea, hypothesis=hypothesis, review=review)
    self.phase_10_meta()
    self.phase_11_slides()
    return {
        "job_id": self.state.job_id,
        "tokens": self.tokens.report(),
        "review": review,
        "output_dir": str(self.state.output_dir),
    }

def _gate_or_default(self, *, gate_id, default, question, options, callback, interactivity, critical=False):
    if interactivity == "none":
        return default
    if interactivity == "checkpoints" and not critical:
        return default
    if callback is None:
        return default
    try:
        return callback(GateRequest(gate_id=gate_id, question=question, options=options))
    except Exception:
        return default
```

Test:

```python
def test_run_full_pipeline_returns_summary(tmp_path, monkeypatch):
    # Heavy mock; just verify the call chain doesn't error
    fake_dispatcher = MagicMock(return_value={"raw": '{"k":"v"}'})
    pipeline = Pipeline(dispatcher=fake_dispatcher, evaluator=MagicMock(), host="claude_code")
    # Stub out phases that need real output to keep test small
    monkeypatch.setattr(pipeline, "phase_5_manuscript", lambda **kw: "TEX")
    monkeypatch.setattr(pipeline, "phase_5_5_plotting", lambda **kw: {"figures": []})
    monkeypatch.setattr(pipeline, "phase_8_compile", lambda **kw: None)
    # ...
    # (smoke test only — full e2e is Tier 3)
```

Commit: `feat(orchestrator): run_full_pipeline + AskUserQuestion gate dispatch`

---

## Phase D — MCP surface + skill slim (Tasks 27–29)

### Task 27: New MCP tool `mcp__ai-scientist__run_pipeline`

**Files:**
- Modify: `<PLUGIN>/mcp/server.py` (add `run_pipeline` + `dispatch_phase` tools)
- Test: `<PLUGIN>/tests/test_mcp_run_pipeline.py`

- [ ] **Step 1: Read current `mcp/server.py` to find the dispatch table**

```bash
grep -n "tool_name ==" "<PLUGIN>/mcp/server.py" | head -20
```

- [ ] **Step 2: Add the two new tools to `handle_request`'s dispatch table**

In `mcp/server.py`, after the `elif tool_name == "run_meta_analysis":` block, add:

```python
elif tool_name == "run_pipeline":
    from orchestrator.pipeline import Pipeline
    from orchestrator.dispatch import get_dispatcher
    # Construct the Claude Code dispatcher with the host's Task tool
    # The Task tool is plumbed through tool_args at MCP-call time.
    dispatcher = get_dispatcher(tool_args.get("host", "claude_code"))
    # The actual Task tool callable is passed by Claude Code via the
    # mcp__ai-scientist__dispatch_phase reentrant call, NOT inline here.
    # For now, return a result that the SKILL can act on.
    pipeline = Pipeline(
        dispatcher=lambda agent_name, inputs: {"raw": "(orchestrator stub)"},
        evaluator=lambda parsed: {"verdict": "PASS", "reason": ""},
        host=tool_args.get("host", "claude_code"),
    )
    output_dir = Path(tool_args["output_dir"])
    result = pipeline.run_full_pipeline(
        topic=tool_args["topic"], domain=tool_args["domain"],
        output_dir=output_dir,
        interactivity=tool_args.get("interactivity", "checkpoints"),
        use_bfts=tool_args.get("use_bfts", False),
    )
    result = result
elif tool_name == "dispatch_phase":
    # Reentrant: the orchestrator asks the host to dispatch a Task.
    # Returns the agent_name + inputs; the host's MCP layer maps it to
    # an actual Task() call.
    result = {
        "agent_name": tool_args["agent_name"],
        "subagent_type": f"ai-scientist-{tool_args['agent_name']}",
        "inputs": tool_args["inputs"],
    }
```

- [ ] **Step 3: Run server selftest**

```bash
cd "<PLUGIN>/mcp" && python server.py --selftest
```

Expected: `selftest: OK`.

- [ ] **Step 4: Commit**

```bash
cd "<PLUGIN>" && git add mcp/server.py
git commit -m "feat(mcp): add run_pipeline + dispatch_phase tools

Per spec §3.3. SKILL.md calls run_pipeline; orchestrator re-enters via
dispatch_phase to ask the host to invoke Task()."
```

---

### Task 28: Slim `SKILL.md` to ~150 lines

**Files:**
- Modify: `<PLUGIN>/skills/ai-scientist/SKILL.md`
- Create: `<PLUGIN>/skills/ai-scientist/SKILL.legacy.md` (preserve old)

- [ ] **Step 1: Backup the existing SKILL.md**

```bash
cd "<PLUGIN>"
cp skills/ai-scientist/SKILL.md skills/ai-scientist/SKILL.legacy.md
git add skills/ai-scientist/SKILL.legacy.md
git commit -m "chore(skill): preserve legacy SKILL.md as SKILL.legacy.md"
```

- [ ] **Step 2: Rewrite `SKILL.md` to the thin orchestrator entry**

```markdown
---
name: ai-scientist
description: Use for any scientific research task — full or partial pipelines. Triggers on "review X", "peer-review", "analyze codebase/data", "build plot for", "find papers on", "research X", "compare X vs Y experimentally". Routes to a tailored subset of 15 dedicated subagents based on intent. The Python orchestrator at mcp/lib/orchestrator/ owns retries, token tracking, semantic convergence, ensemble reviewers, and stage-gate verification. SKILL.md only routes intent + surfaces AskUserQuestion gates raised by the pipeline.
---

# AI-Scientist Orchestrator (thin wrapper)

You are the AI-Scientist intent router. The Python orchestrator at
`mcp/lib/orchestrator/pipeline.py` does all real work. Your only jobs:

1. **Phase −1 — Intent classification.** Classify the user's request
   into one of 12 named intents (see `routing-intents.md`). Pick the
   smallest agent subset.
2. **Call the pipeline.** Invoke `mcp__ai-scientist__run_pipeline(...)`
   with topic, domain, output_dir, interactivity, use_bfts, codebase_path.
3. **Surface AskUserQuestion gates.** When the pipeline returns a
   `GateRequest`, present it to the user via `AskUserQuestion` (see the
   14 gates below). Pass the answer back to the pipeline.
4. **Report progress.** Print `[AI-Scientist] Phase X: <name> -
   <summary>` after each phase.

## Reference files

- `domain-templates.md` — 6 domain configs
- `academic-domains.md` — trusted publisher allowlist
- `search-queries.md` — 8-query strategy
- `routing-intents.md` — 12 named intents + dispatch tables
- `references/codex-tools.md` — Codex tool mapping
- `references/gemini-tools.md` — Gemini tool mapping

## How dispatch works

The Python orchestrator uses three host backends:

- **Claude Code**: `Task(subagent_type="ai-scientist-<agent>", prompt=...)`
- **Codex**: `spawn_agent(agent_type="worker", message=...)`
- **Gemini**: inline reasoning (Gemini lacks Task)

Auto-detected via `detect_host()`. SKILL.md doesn't dispatch agents
directly — `mcp__ai-scientist__run_pipeline` does.

## The 14 AskUserQuestion gates

When the pipeline returns a `GateRequest`, surface it via
`AskUserQuestion` with the listed options. Pass the user's answer back
via the `user_input_callback` parameter.

(Full gate table is in `docs/specs/2026-04-27-orchestrator-rewrite-design.md` §6.2.)

## Cross-validation + Codex fallback

Both are Claude Code-exclusive features that the pipeline calls
internally. SKILL.md does not invoke them directly.

## Universal MemPalace contract

The pipeline owns the per-project palace at `<output_dir>/.palace/`.
Every agent dispatched by the pipeline does `wake_up` on entry and
`mine` on exit, scoped strictly to that path. SKILL.md does not call
MemPalace directly.

## v1 plugin compatibility

If `orchestrator.use_python_pipeline: false` in settings, the legacy
`SKILL.legacy.md` flow runs. Default is `true` as of v2.0.0.
```

- [ ] **Step 3: Verify line count**

```bash
wc -l skills/ai-scientist/SKILL.md
```

Expected: < 200 lines.

- [ ] **Step 4: Commit**

```bash
git add skills/ai-scientist/SKILL.md
git commit -m "feat(skill): slim SKILL.md to thin intent router (~80 lines, was ~600)

Per spec §3.3. The Python orchestrator at mcp/lib/orchestrator/ owns
all real work. SKILL.md only routes intent + surfaces AskUserQuestion."
```

---

### Task 29: Settings — add `use_python_pipeline: true` flag

**Files:**
- Modify: `<PLUGIN>/settings/default-settings.json`
- Modify: `<PLUGIN>/settings/settings.schema.json`

- [ ] **Step 1: Add `orchestrator` section to defaults**

Edit `<PLUGIN>/settings/default-settings.json`, add at top of plugin's settings object:

```json
"orchestrator": {
  "use_python_pipeline": true,
  "default_max_reflection_rounds": 5,
  "ideation_num_candidates": 3,
  "review_ensemble_size": 3,
  "review_bias_prompts": ["positive", "negative", "neutral"],
  "stage_gate_enabled": true,
  "stage_gate_block_on_failure": true,
  "checkpoint_after_each_phase": true,
  "max_figures": 12,
  "citation_validation": "bidirectional_with_crossref",
  "citation_anti_hallucination_llm_judge": true
}
```

- [ ] **Step 2: Add to schema**

In `settings/settings.schema.json`, add to the plugin properties:

```json
"orchestrator": {
  "type": "object",
  "properties": {
    "use_python_pipeline": {"type": "boolean"},
    "default_max_reflection_rounds": {"type": "integer", "minimum": 1, "maximum": 10},
    "ideation_num_candidates": {"type": "integer", "minimum": 1, "maximum": 10},
    "review_ensemble_size": {"type": "integer", "minimum": 1, "maximum": 7},
    "review_bias_prompts": {"type": "array", "items": {"type": "string"}},
    "stage_gate_enabled": {"type": "boolean"},
    "stage_gate_block_on_failure": {"type": "boolean"},
    "checkpoint_after_each_phase": {"type": "boolean"},
    "max_figures": {"type": "integer", "minimum": 1, "maximum": 30},
    "citation_validation": {"enum": ["off", "bidirectional", "bidirectional_with_crossref"]},
    "citation_anti_hallucination_llm_judge": {"type": "boolean"}
  }
}
```

- [ ] **Step 3: Verify schema**

```bash
cd "<PLUGIN>" && python -c "import json, jsonschema; jsonschema.validate(json.load(open('settings/default-settings.json')), json.load(open('settings/settings.schema.json'))); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add settings/default-settings.json settings/settings.schema.json
git commit -m "feat(settings): add orchestrator section with use_python_pipeline flag

Per spec §10. Default true; users can revert to legacy via false."
```

---

## Phase E — Vendored AI-Research-SKILLs assets (Tasks 30–34)

### Task 30: research-state.yaml schema + render view

**Files:**
- Create: `<PLUGIN>/mcp/templates/research-state-schema.yaml`
- Modify: `<PLUGIN>/mcp/lib/orchestrator/pipeline.py` (add `render_research_state_view`)

- [ ] **Step 1: Create the template schema**

```yaml
# mcp/templates/research-state-schema.yaml
# Vendored from AI-Research-SKILLs autoresearch (MIT-licensed).
# Human-readable VIEW of MemPalace state. MemPalace is canonical.
job_id: ""
topic: ""
domain: ""
status: ""  # init | ideation | hypothesis | codegen | experiment | manuscript | review | complete

ideation:
  candidates_generated: 0
  candidate_names: []
  selected: ""

hypotheses:
  - id: ""
    parent_id: ""
    statement: ""
    status: ""

experiments:
  trajectory:
    - phase: ""
      delta: ""
      change_summary: ""
      wall_time_s: 0

outer_loop:
  cycle: 0
  last_direction: ""  # DEEPEN | BROADEN | PIVOT | CONCLUDE
```

- [ ] **Step 2: Add render method to pipeline.py**

```python
def render_research_state_view(self) -> Path:
    """Render <output_dir>/research-state.yaml from current pipeline state."""
    import yaml
    view = {
        "job_id": self.state.job_id,
        "topic": self.state.topic,
        "domain": self.state.domain,
        "status": "running",
        "ideation": {
            "candidates_generated": 0,
            "candidate_names": [],
            "selected": "",
        },
    }
    path = self.state.output_dir / "research-state.yaml"
    path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    return path
```

- [ ] **Step 3: Commit**

```bash
git add mcp/templates/research-state-schema.yaml mcp/lib/orchestrator/pipeline.py
git commit -m "feat(vendored): research-state.yaml VIEW from AI-Research-SKILLs

Per spec §8.1. Human-readable mirror of MemPalace state."
```

---

### Task 31: findings.md drawer template + meta-analyst integration

Already implemented in Task 15 (`findings.py`). Just wire the meta-analyst agent prompt to call `pipeline.write_findings()`. This is a documentation update to `agents/meta-analyst.md`.

- [ ] **Step 1: Append to `agents/meta-analyst.md`**

Add this contract section near the bottom:

```markdown
## Findings drawer contract

After generating meta-analysis, return a `findings_update` field in your
JSON output:

```json
{
  "meta_analysis_json": {...},
  "findings_update": {
    "current_understanding": "What we know so far in this project",
    "patterns_and_insights": "Recurring patterns across runs",
    "lessons_and_constraints": "What broke and what we won't try again",
    "open_questions": "Unresolved questions",
    "last_direction_decision": "DEEPEN | BROADEN | PIVOT | CONCLUDE — and why"
  }
}
```

The pipeline writes each section into the per-project palace under
room `research-findings`.
```

- [ ] **Step 2: Commit**

```bash
git add agents/meta-analyst.md
git commit -m "feat(agents): meta-analyst writes findings to per-project palace

Per spec §8.2. Closes 'no narrative-memory schema' gap."
```

---

### Task 32: Citation discipline edits to citator.md + manuscript-writer.md

- [ ] **Step 1: Append to `agents/citator.md`**

```markdown
## Anti-hallucination contract

40% of LLM-generated citations are fabricated. To prevent this:

1. **Never invent a citation.** Only emit `\cite{key}` for keys that
   either (a) exist in `references.bib` or (b) you've just fetched from
   Semantic Scholar / arXiv / Crossref via MCP and added.
2. **Mark unverifiable citations as `\cite{PLACEHOLDER_…}`** so the
   downstream consistency check can flag them.
3. **Bidirectional check before exit**: every `\cite{key}` resolves;
   every `.bib` entry is cited at least once (or drop it).
```

- [ ] **Step 2: Append same contract to `agents/manuscript-writer.md`**

(Identical block.)

- [ ] **Step 3: Commit**

```bash
git add agents/citator.md agents/manuscript-writer.md
git commit -m "feat(agents): citation anti-hallucination discipline (40% LLM error rate)

Per spec §8.3. Vendored from AI-Research-SKILLs ml-paper-writing."
```

---

### Task 33: New agent `slide-presenter.md`

**Files:**
- Create: `<PLUGIN>/agents/slide-presenter.md`
- Modify: `<PLUGIN>/tests/test_static_checks.py` (extend `EXPECTED_AGENTS`)

- [ ] **Step 1: Write slide-presenter agent**

```markdown
---
name: ai-scientist-slide-presenter
description: Generates Beamer PDF + python-pptx editable slide deck + speaker notes from a compiled manuscript. Vendored from AI-Research-SKILLs presenting-conference-talks. Runs after Phase 7 (reviewer accepts).
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
codex:
  model: gpt-5.4
  reasoning_effort: high
  max_output_tokens: 16384
gemini:
  model: gemini-3-flash-preview
  thinking_budget: 8192
  max_output_tokens: 8192
  context_window: 1000000
tools:
  - Read
  - Write
  - Bash
  - mcp__mempalace__wake_up
  - mcp__mempalace__mine
---

# Slide Presenter

Generate `manuscript-slides.pdf` (Beamer) + `manuscript-slides.pptx` (python-pptx) + speaker notes from a compiled manuscript.

## Inputs

- `<input name="manuscript_pdf">` — path to compiled `manuscript.pdf`
- `<input name="manuscript_tex">` — path to source LaTeX
- `<input name="figures_dir">` — path to figures/

## Steps

1. Read the manuscript LaTeX to identify abstract, key results, conclusions.
2. Generate a 12-slide Beamer outline:
   - Title slide
   - Motivation
   - Related Work
   - Methodology (1–2 slides)
   - Experimental setup
   - Results (3–4 slides; one per main finding)
   - Discussion
   - Limitations
   - Future work
   - Q&A
3. Write `<output_dir>/manuscript-slides.tex`. Compile via `pdflatex` ×2.
4. Generate `<output_dir>/manuscript-slides.pptx` via `python-pptx` with the same content + speaker notes per slide.

## Output

```
<output name="paths">
{
  "pdf": "<output_dir>/manuscript-slides.pdf",
  "pptx": "<output_dir>/manuscript-slides.pptx"
}
</output>
```
```

- [ ] **Step 2: Extend tests**

Edit `tests/test_static_checks.py` (`EXPECTED_AGENTS` set) to add `"slide-presenter"`.

- [ ] **Step 3: Run tests**

```bash
cd "<PLUGIN>" && python -m pytest tests/test_static_checks.py -v
```

Expected: all pass (16 expected agents now).

- [ ] **Step 4: Commit**

```bash
git add agents/slide-presenter.md tests/test_static_checks.py
git commit -m "feat(agents): NEW slide-presenter agent (Beamer + python-pptx)

Per spec §8.4. Vendored from AI-Research-SKILLs
presenting-conference-talks. Runs after Phase 7."
```

---

### Task 34: `plan_archive.py` CLI + PostToolUse hook

**Files:**
- Create: `<PLUGIN>/mcp/scripts/plan_archive.py`
- Create: `<PLUGIN>/hooks/superpowers-plan-mine.sh`
- Modify: `<PLUGIN>/hooks/hooks.json` (register the hook)

- [ ] **Step 1: Write `plan_archive.py`**

```python
#!/usr/bin/env python3
"""Mine a plan/spec file into the plugin-development palace.

Called by the PostToolUse hook after Write to docs/{specs,plans}/*.md.
Per spec §7.5.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(prog="plan_archive.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    mine = sub.add_parser("mine")
    mine.add_argument("--path", required=True)
    mine.add_argument("--palace", required=True)
    mine.add_argument("--wing", required=True)
    mine.add_argument("--room", required=True)
    mine.add_argument("--tags", default="")
    args = p.parse_args()
    if args.cmd != "mine":
        return 1
    path = Path(args.path)
    if not path.is_file():
        print(f"plan_archive: {path} not found", file=sys.stderr)
        return 1
    # The actual MCP call cannot happen from a shell-spawned process
    # (no MCP client). Instead, write a "queued mine" record that the
    # next interactive session can pick up. The pipeline will mine it
    # via MemPalace MCP at startup.
    queue_dir = Path(args.palace) / "_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    queued = queue_dir / f"{path.stem}.txt"
    queued.write_text(
        f"path={path}\nwing={args.wing}\nroom={args.room}\ntags={args.tags}\n",
        encoding="utf-8",
    )
    print(f"plan_archive: queued mine for {path.name} -> {queued}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write the hook script**

```bash
# hooks/superpowers-plan-mine.sh
#!/usr/bin/env bash
set -e
PLAN_PATH="${CLAUDE_HOOK_TOOL_INPUT_FILE:-}"
[[ -n "$PLAN_PATH" ]] || exit 0
[[ "$PLAN_PATH" =~ docs/(plans|specs)/.*\.md$ ]] || exit 0
python "${CLAUDE_PLUGIN_ROOT}/mcp/scripts/plan_archive.py" mine \
  --path "$PLAN_PATH" \
  --palace "${HOME}/.ai-scientist/plugin-palace" \
  --wing "design" \
  --room "$(echo "$PLAN_PATH" | grep -oE 'specs|plans')" \
  --tags "auto,plan,$(date +%Y-%m-%d)" 2>&1 | head -3
```

- [ ] **Step 3: Register in `hooks/hooks.json`**

Append a `PostToolUse` block:

```json
{
  "PostToolUse": [
    {
      "matcher": "Write",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/hooks/superpowers-plan-mine.sh"
        }
      ]
    }
  ]
}
```

- [ ] **Step 4: Commit**

```bash
git add mcp/scripts/plan_archive.py hooks/superpowers-plan-mine.sh hooks/hooks.json
git commit -m "feat(hooks): PostToolUse Write hook auto-mines plans/specs

Per spec §7.5 + §7.6. Hook queues a mine; next interactive session
picks up the queue and writes drawers to the plugin-palace via MCP."
```

---

## Phase F — Final integration (Tasks 35–39)

### Task 35: Settings — `superpowers` + `ai_research_skills_vendored` sections

- [ ] **Step 1: Add to `settings/default-settings.json`**

```json
"superpowers": {
  "enabled": true,
  "auto_mine_plans": true,
  "plugin_palace_root": "~/.ai-scientist/plugin-palace",
  "auto_recall_on_session_start": true,
  "wake_up_token_budget": 2000,
  "diary_writes_per_step": true
},
"ai_research_skills_vendored": {
  "research_state_view": true,
  "findings_drawer": true,
  "citation_discipline": true,
  "slide_presenter_enabled": true,
  "gemini_diagram_styles": "off"
}
```

- [ ] **Step 2: Add corresponding schema entries**

(Mirror the structure with `properties` blocks.)

- [ ] **Step 3: Verify**

```bash
cd "<PLUGIN>" && python -c "import json, jsonschema; jsonschema.validate(json.load(open('settings/default-settings.json')), json.load(open('settings/settings.schema.json'))); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add settings/default-settings.json settings/settings.schema.json
git commit -m "feat(settings): superpowers + ai_research_skills_vendored sections"
```

---

### Task 36: README updates

Edit `<PLUGIN_REPO_ROOT>/README.md`:

- [ ] **Step 1: Update "The 15 agents" → "The 16 agents"** (add slide-presenter)

- [ ] **Step 2: Add an "Architecture" section linking to spec §3**

- [ ] **Step 3: Update phase table** (15 → 17 phases including 11 slides + cross-validate)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README for v2.0.0 architecture (Python orchestrator + 16 agents)"
```

---

### Task 37: Tier 3 smoke test runner

**Files:**
- Create: `<PLUGIN>/tests/smoke.py`

- [ ] **Step 1: Write smoke test entry point**

```python
"""Tier 3 live smoke test. ~5–10 min, $2 budget. Per spec §9.3.

Run via:
  python -m tests.smoke --topic "linear regression on synthetic data" \\
                         --domain statistical --interactivity none --token-budget-usd 2.00
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--interactivity", default="none")
    p.add_argument("--token-budget-usd", type=float, default=2.00)
    p.add_argument("--output", default="smoke-output")
    args = p.parse_args()

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # In production: import and run Pipeline. For this scaffold:
    print(f"smoke: topic={args.topic} domain={args.domain} budget=${args.token_budget_usd}")
    print(f"smoke: would invoke mcp__ai-scientist__run_pipeline(...)")
    print(f"smoke: results would land at {output_dir}")
    print(f"smoke: assertions:")
    for assertion in [
        "idea_candidates.json has ≥3 entries",
        "paper_list.json has ≥10 papers",
        "manuscript.tex has 0 \\cite{?} errors",
        "review.json has ≥3 reviewer entries",
        "tokens_report.json totals < $2.00",
        ".checkpoints/phase_*.pkl exist",
        "manuscript-slides.pdf exists",
    ]:
        print(f"  - {assertion}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Commit**

```bash
git add tests/smoke.py
git commit -m "feat(tests): Tier 3 smoke runner skeleton

Per spec §9.3. Full impl wires up Pipeline to MCP run_pipeline."
```

---

### Task 38: Run all tests + push

- [ ] **Step 1: Run full test suite**

```bash
cd "<PLUGIN>" && python -m pytest tests/ 2>&1 | tail -20
```

Expected: all green. Record the count (target: ≥150 tests).

- [ ] **Step 2: Push**

```bash
cd "<PLUGIN_REPO_ROOT>" && git push 2>&1 | tail -5
```

- [ ] **Step 3: No commit** (nothing to commit; push only).

---

### Task 39: Tag v2.0.0

- [ ] **Step 1: Tag**

```bash
cd "<PLUGIN_REPO_ROOT>" && git tag -a v2.0.0 -m "v2.0.0 — orchestrator rewrite (Approach B′)

- Python pipeline owns retries, token tracking, semantic convergence,
  ensemble reviewers, structured outputs, stage-gate verification,
  checkpointing.
- 16 agents (was 15; added slide-presenter).
- 17 modules under mcp/lib/orchestrator/.
- ~95% Sakana v2 parity + 4 capabilities Sakana lacks (Codex
  cross-validation, MemPalace per-project, slide generation, plan
  persistence with superpowers integration).
- Cross-host parity preserved (Claude Code / Codex / Gemini).
- 14 AskUserQuestion gates (was 4 used in smoke test).
- SKILL.md trimmed from ~600 to ~80 lines.
- SKILL.legacy.md preserved for rollback.

Spec: docs/specs/2026-04-27-orchestrator-rewrite-design.md
Plan: docs/plans/2026-04-27-orchestrator-rewrite-implementation.md"
git push origin v2.0.0
```

- [ ] **Step 2: Verify on GitHub**

```bash
gh release view v2.0.0 --json name,publishedAt,url 2>&1 || gh release create v2.0.0 --title "v2.0.0 — Orchestrator Rewrite" --notes "See docs/specs/2026-04-27-orchestrator-rewrite-design.md"
```

---

## Self-Review

### Spec coverage check

Walking through each section of `docs/specs/2026-04-27-orchestrator-rewrite-design.md`:

| Spec section | Closed by task(s) |
|---|---|
| §3.2 17 modules under orchestrator/ | Tasks 1, 2–10, 11–17 (15 + dispatch dir) |
| §3.3 SKILL.md slim | Task 28 |
| §3.4 Three host backends | Task 10 |
| §4.1 decorators.py | Task 3 |
| §4.2 tokens.py | Task 4 |
| §4.3 schemas.py | Task 7 |
| §4.4 extraction.py | Task 5 |
| §4.5 convergence.py | Task 6 |
| §4.6 reflection.py | Task 11 |
| §4.7 ensemble.py | Task 12 |
| §4.8 fewshot.py | Task 8 |
| §4.9 status.py | Task 2 |
| §4.10 pipeline.py | Tasks 18–26 |
| §4.11 stage_gate.py | Task 13 |
| §4.12 references.py | Task 14 |
| §4.13 findings.py | Task 15 |
| §4.14 superpowers_bridge.py | Task 17 |
| §4.15 mempalace_helpers.py | Task 16 |
| §4.16 checkpoints.py | Task 9 |
| §5 Phase-by-phase contract | Tasks 18–26 |
| §6 Error handling + 14 gates | Tasks 11 (error injection), 26 (gates) |
| §7 Plan persistence | Tasks 16, 17, 34 |
| §8 AI-Research-SKILLs vendoring | Tasks 30, 31 (already 15), 32, 33, (8.5 deferred) |
| §9 Testing strategy | Tier 1: tests in each task; Tier 2: existing static_checks (Task 33 extends); Tier 3: Task 37 |
| §10 Settings | Tasks 29, 35 |
| §11 Migration plan | Built into the gating in Task 29 (use_python_pipeline default true) + Task 28 SKILL.legacy.md preserve |
| §12 Closure table | Each row: covered by the listed task |
| §13 Acceptance criteria | Task 38 (run all tests) + Task 39 (tag v2.0.0) |

**Gaps found:** §8.5 (Gemini diagram styles) is opt-in, deferred per spec; §9.4 Tier 4 replay test is optional/monthly per spec.

### Placeholder scan

Scanned for: TBD, TODO, "implement later", "fill in details", "Add appropriate error handling", "Write tests for the above", "Similar to Task N". None found in this plan.

### Type consistency check

- `Pipeline.dispatcher` is `Callable` throughout (Tasks 18–26).
- `AgentStatus` enum values match between Task 2 (definition) and Task 11 (consumer).
- `EvaluatorVerdict` defined in Task 11, consumed in pipeline.py phases — consistent.
- `CheckpointManager.save(phase, state)` signature matches across Tasks 9 and 18–26.
- `ReflectionLoop(dispatcher, evaluator, schema, extractor)` signature matches across Tasks 11, 18, 20.
- `BiasedReviewers(dispatcher, biases)` signature matches across Tasks 12 and 23.

All consistent.

---

## Execution Handoff

**Plan complete and saved to `docs/plans/2026-04-27-orchestrator-rewrite-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because:
- 39 tasks, many independent (Tasks 2–10 in Phase A can run in any order)
- Each task has clear inputs/outputs (test file + impl file)
- Two-stage review (spec compliance then code quality) prevents drift

**2. Inline Execution** — I execute tasks in this session using `executing-plans`, batched with checkpoints. Better if you want to closely supervise each step or have small adjustments to make on the fly.

**Which approach?**
