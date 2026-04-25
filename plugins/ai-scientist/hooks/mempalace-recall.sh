#!/usr/bin/env bash
# SessionStart hook: ask MemPalace for relevant context for the current job.
#
# Behavior:
#   - If no active ai-scientist job, exit 0 silently.
#   - If a job is in progress (config.json exists in $AI_SCIENTIST_OUTPUT_DIR),
#     run `mempalace wake-up` scoped to that job's palace and emit a compact
#     context summary on stdout for the agent to consume.
#
# Triggered automatically by Claude Code / Codex on session start.

set -euo pipefail

PALACE_ROOT="${MEMPALACE_ROOT:-$HOME/.ai-scientist/palace}"
JOB_DIR="${AI_SCIENTIST_OUTPUT_DIR:-}"

if [[ -z "$JOB_DIR" || ! -f "$JOB_DIR/config.json" ]]; then
  # No active job — nothing to recall. Exit quietly.
  exit 0
fi

JOB_ID=$(python -c "import json,sys; print(json.load(open('$JOB_DIR/config.json'))['job_id'])" 2>/dev/null || echo "unknown")
JOB_PALACE="$PALACE_ROOT/$JOB_ID"

if [[ ! -d "$JOB_PALACE" ]]; then
  # No palace yet for this job. Nothing to recall.
  exit 0
fi

# Wake up: emit a compact context summary on stdout. Token budget honored
# via MEMPALACE_WAKE_BUDGET (default 4000). Output goes to the agent.
mempalace wake-up --root "$JOB_PALACE" --token-budget "${MEMPALACE_WAKE_BUDGET:-4000}" 2>/dev/null || true
