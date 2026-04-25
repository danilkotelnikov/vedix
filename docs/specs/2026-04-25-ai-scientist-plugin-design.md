# AI-Scientist Plugin — Design Spec

- **Date:** 2026-04-25
- **Author:** scienceboylovesyou@gmail.com
- **Status:** Approved for implementation planning
- **Implements:** Reproduction of `~/.claude/skills/ai-scientist/SKILL.md` + `~/.ai-scientist/mcp_server.py` as a first-class Claude Code plugin

---

## 1. Goals

Reproduce the existing AI-Scientist v2 research pipeline as a proper Claude Code plugin so it:

1. Appears in Claude Code's **Customize** menu (installable via local marketplace).
2. Decomposes orchestration into **12 dedicated subagents**, each with a pinned model and thinking budget.
3. Supports **mid-session model switching** (each `Task()` dispatch spawns a fresh subagent at its pinned model — no `/model` command needed).
4. Exposes a **detailed tweaking surface** via `settings.json` and CLI flags (every model, thinking budget, phase, and external service is overridable).
5. Auto-triggers on **natural-language requests** ("review X", "plot Y", "find papers on Z") by routing to the smallest agent subset that satisfies the intent.
6. Replaces silent partial-state failures with **Fixer-driven user-in-the-loop recovery**.
7. Produces manuscripts in **both LaTeX and Word**, with a **visual validation pass** on the rendered output.

## 2. Non-Goals (YAGNI)

- CI/CD integration — local plugin, no GitHub Actions in v1.
- Streaming UI for long-running pipelines — terminal output is sufficient.
- Multi-user knowledge-store sharing — single-user, single-machine.
- Custom domain templates beyond the existing 6 — extension via PRs, not config.
- Replacing the underlying Python lib (`knowledge_store.py`, `chroma_store.py`, etc.) — these are reused as-is, only re-homed inside the plugin.

## 3. Architecture — Approach B (skill owns I/O, agents own thinking)

The orchestrator skill is the conductor. It owns:

- Argument parsing, output-dir creation, `config.json` writing.
- All cross-phase file I/O (read `paper_list.json`, inline relevant slices into Hypothesizer's prompt, persist Hypothesizer's return to `hypothesis.md`).
- Dependency installation (`pip install -r requirements.txt` inside per-job venv).
- BibTeX dedup/merge, knowledge indexing, MCP-direct calls.
- Intent classification and agent routing.

Agents own only the LLM-thinking part of their phase. Each agent has a tight contract: receives inlined inputs (under `<input name="...">` tags in its prompt), returns a structured payload (JSON or LaTeX/Python text block, marked with `<output name="...">`).

**Why Approach B over pure delegation:** subagents cannot read parent context. Pure delegation would force the orchestrator to inline a 50-paper JSON (~40 KB) into the Hypothesizer's prompt and parse it back as a string. Hybrid keeps the deterministic plumbing in the skill, where it can persist intermediate state to disk and re-read compact slices per phase. Result: lean orchestrator context, focused agent prompts.

## 4. Plugin layout

```
C:\Users\danil\OneDrive\Рабочий стол\MCPs\ai-scientist-plugin\
├── .claude-plugin\
│   ├── plugin.json                  # manifest (name, version, author, description)
│   └── marketplace.json             # local marketplace pointer
├── README.md                        # quickstart + tweaking guide
├── LICENSE
│
├── agents\                          # 12 subagent definitions
│   ├── ideator.md                   # opus, 48k thinking
│   ├── codebase-scanner.md          # sonnet, 8k
│   ├── literature-searcher.md       # sonnet, 8k (orchestrates 6 parallel API calls inside)
│   ├── hypothesizer.md              # opus, 64k
│   ├── code-generator.md            # opus, 48k
│   ├── experiment-runner.md         # sonnet, 8k
│   ├── plotter.md                   # sonnet, 8k
│   ├── manuscript-writer.md         # opus, 48k (orchestrates 6 parallel section subagents inside)
│   ├── citator.md                   # sonnet, 8k
│   ├── reviewer.md                  # opus, 64k
│   ├── meta-analyst.md              # sonnet, 8k
│   └── fixer.md                     # sonnet, 16k (diagnostician)
│
├── skills\
│   └── ai-scientist\
│       ├── SKILL.md                 # ~600-line orchestrator (slimmer than current 1076)
│       ├── domain-templates.md      # 6 domain configs (ml/optimization/.../software_engineering)
│       ├── academic-domains.md      # trusted-publisher allowlist
│       ├── search-queries.md        # 8-query strategy + Q-pattern templates
│       └── routing-intents.md       # 12 named intents + dispatch tables (Section 8)
│
├── commands\
│   ├── ai-scientist.md              # /ai-scientist <topic> [flags]
│   ├── ai-scientist-list.md         # /ai-scientist-list
│   ├── ai-scientist-output.md       # /ai-scientist-output <job-id> [section]
│   ├── ai-scientist-query.md        # /ai-scientist-query <terms>
│   ├── ai-scientist-meta.md         # /ai-scientist-meta
│   └── ai-scientist-resume.md       # /ai-scientist-resume <job-id>
│
├── mcp\
│   ├── .mcp.json                    # registers ai-scientist MCP for plugin scope
│   ├── server.py                    # mcp_server.py refactored to import from lib/
│   ├── lib\                         # 8 modules from ~/.ai-scientist/lib/
│   │   ├── __init__.py
│   │   ├── knowledge_store.py
│   │   ├── chroma_store.py
│   │   ├── codebase_analyzer.py
│   │   ├── experiment_runner.py
│   │   ├── manuscript_coordinator.py
│   │   ├── meta_analyzer.py
│   │   └── sqlite_store.py
│   ├── templates\
│   │   ├── latex\
│   │   │   ├── aiscientist-default.tex
│   │   │   ├── overleaf-minimal.tex
│   │   │   ├── elsevier-cas-sc.tex
│   │   │   ├── ieee-conference.tex
│   │   │   └── acm-sig.tex
│   │   └── word\                    # found author-shared templates (license-verified)
│   │       ├── arxiv-shared-1.docx
│   │       ├── minimalist.docx
│   │       └── two-column-academic.docx
│   └── requirements.txt             # chromadb, sentence-transformers, etc.
│
├── settings\
│   ├── default-settings.json        # plugin defaults
│   └── settings.schema.json         # JSON Schema for editor linting
│
├── tests\
│   └── routing-fixtures.json        # 12 intent-classification fixtures
│
├── docs\
│   └── specs\
│       └── 2026-04-25-ai-scientist-plugin-design.md   # this file
│
└── scripts\
    ├── install.ps1                  # one-time setup (venv, pip, probe pandoc/libreoffice/pdflatex)
    ├── migrate-from-skill.ps1       # archives old skill, verifies plugin
    ├── rollback.ps1                 # restores old skill if user reverts
    └── verify.ps1                   # static + MCP smoke + routing tests
```

**Runtime data** stays at `~/.ai-scientist/` (`knowledge.db`, `jobs.json`, `trajectories.jsonl`, `meta_analysis.json`, `what_works.json`) so it survives plugin reinstalls.

## 5. Agents

Each agent file follows this frontmatter shape:

```yaml
---
name: ai-scientist-<role>
description: <when the orchestrator dispatches this agent>
model: opus | sonnet
thinking:
  enabled: true | false
  budget_tokens: <see table>
tools:
  - <least-privilege list>
---
```

| # | Agent | Model | Thinking budget | Key tools |
|---|---|---|---|---|
| 1 | ideator | opus | 48,000 | WebFetch, Read, AskUserQuestion (checkpoint), `mcp__ai-scientist__search_knowledge_index`, `mcp__ai-scientist__get_meta_analysis` |
| 2 | codebase-scanner | sonnet | 8,000 | Glob, Grep, Read, Bash, `mcp__ai-scientist__analyze_codebase` |
| 3 | literature-searcher | sonnet | 8,000 | WebFetch, `mcp__arxiv__*`, `mcp__biorxiv__*`, `mcp__pubmed__*`, `mcp__annas-mcp__*` |
| 4 | hypothesizer | opus | 64,000 | Read, Write, AskUserQuestion (checkpoint), `mcp__ai-scientist__search_knowledge_index` |
| 5 | code-generator | opus | 48,000 | Read, Write |
| 6 | experiment-runner | sonnet | 8,000 | Bash, Read, Edit, Write |
| 7 | plotter | sonnet | 8,000 | Read, Write, Bash, AskUserQuestion (checkpoint) |
| 8 | manuscript-writer | opus | 48,000 | Read, Write, Task (for nested section subagents) |
| 9 | citator | sonnet | 8,000 | Read, Edit, Write, WebFetch |
| 10 | reviewer | opus | 64,000 | Read (multimodal — sees rendered PNGs), Write, AskUserQuestion (checkpoint) |
| 11 | meta-analyst | sonnet | 8,000 | Read, Write, `mcp__ai-scientist__run_meta_analysis` |
| 12 | fixer | sonnet | 16,000 | Read, AskUserQuestion |

**Two agents act as nested orchestrators:**

- **`manuscript-writer`** internally `Task()`s 6 section subagents in parallel (Abstract, Introduction, Methods, Results, Discussion, Conclusion). Each section subagent runs on Opus and inherits its thinking budget from the parent's frontmatter (settable per-section in v1.1 — see Section 15). This preserves the parallelism in the original Phase 5 without exposing 6 more top-level agent files.
- **`literature-searcher`** internally invokes 6 sources (Semantic Scholar, OpenAlex, arXiv, bioRxiv/PubMed, Consensus, Anna's Archive) as parallel WebFetch + MCP calls (not nested Task spawns — these are tool calls that share the agent's context). Throttled per Section 9.

**Top-level thinking-budget total** (excluding the 6 nested manuscript-section subagents and conditional Fixer dispatches): 272,000 tokens across 5 Opus agents (48k + 64k + 48k + 48k + 64k) and 48,000 tokens across 6 Sonnet agents (6 × 8k). Fixer adds 16k per dispatch on failure. Nested manuscript-section subagents add up to 6 × 48k when ManuscriptWriter inherits its budget down. All values overridable via settings.

## 6. Orchestration flow

| Phase | Phase name | Owner | Output artifact |
|---|---|---|---|
| -1 | Intent classification | skill | (in-memory route decision) |
| 0 | Init | skill | `config.json` |
| 0.5 | Ideation | ideator | `idea.json` |
| 0.75 | Codebase scan (optional) | codebase-scanner | `codebase_analysis.json` |
| 1 | Literature search | literature-searcher | `paper_list.json`, `references.bib`, `validation_log.json` |
| 2 | Hypothesis | hypothesizer | `hypothesis.md`, `equations.txt` |
| 3 | Codegen | code-generator | `experiment.py`, `requirements.txt` |
| 4 | Experiment run | experiment-runner | `experiment_stdout.txt`, `experiment_stderr.txt`, `results.csv`, `*.npy`, `figures/`, `experiment_fix_log.json` |
| 5.5 | Plot aggregation | plotter | `auto_plot_aggregator.py`, refined `figures/` |
| 5 | Manuscript | manuscript-writer (with 6 nested section subagents) | `manuscript.tex` |
| 6 | Citation enrichment | citator | updated `references.bib` |
| 7 | Self-review | reviewer | `review.json`, `manuscript_v2.tex` |
| 8 | LaTeX compile | skill | `manuscript.pdf` |
| 8.25 | Word export | skill (uses Pandoc; falls back to anthropic-skills:docx) | `manuscript.docx` |
| 8.5 | Visual validation | reviewer (multimodal pass) | `visual_review.json` |
| 9 | Knowledge indexing | skill | appends to `~/.ai-scientist/knowledge/*.jsonl` + DB |
| 10 | Meta-analysis | meta-analyst (or skill-direct MCP call) | `meta_analysis.json`, `what_works.json` |

**Data passing rule:** orchestrator reads required files before each dispatch, inlines them into the agent's prompt under `<input name="...">` tags, parses the agent's `<output name="...">`-marked return, and writes to the canonical artifact path. The orchestrator never accumulates a phase's full output in its own context — it persists and re-reads compact slices.

**Mid-session model switching:** each `Task(subagent_type=...)` call spawns a fresh subagent at its pinned model from frontmatter. The orchestrator session can be on any model; per-phase swapping is automatic with no `/model` command needed.

## 7. Error handling — Fixer agent + user-in-the-loop

**No silent partial-state proceed.** When any phase fails or returns malformed output:

1. Skill captures failure context: phase name, error class (network / dependency / schema-mismatch / runtime / timeout / output-parse), full stderr, current on-disk state.
2. Skill dispatches Fixer with that bundle. Fixer diagnoses root cause and returns 2–4 concrete fix options.
3. Skill surfaces the diagnosis + options to the user via `AskUserQuestion`.
4. User picks → skill applies the fix and re-dispatches the original agent. Up to `fixer_max_rounds_per_phase` (default 3) per phase. After exhaustion: "I've tried 3 fixes, here's the state, what now?" — escalation prompt with full state dump.
5. State on disk is always either correct or marked as `<phase>_failed.json` with a structured failure record. No empty `paper_list.json`, no skipped Phase 5 without an explicit user decision.

**Fixer's failure-class taxonomy:**

| Class | Examples | Typical fixes |
|---|---|---|
| network | API 429, DNS failure, timeout to OpenAlex | retry with backoff, switch source, set OPENALEX_EMAIL |
| dependency | ModuleNotFoundError, pip resolution conflict | add to requirements.txt, pin version, use alternate package |
| schema | agent returned non-JSON, missing required field | re-prompt with schema reminder, ask user to specify missing field |
| runtime | TypeError, ValueError, FileNotFoundError in experiment.py | patch specific line, simplify computation, switch to synthetic data |
| timeout | experiment >300s | reduce data size, simplify model, raise timeout |
| output-parse | manuscript missing section, BibTeX malformed | regenerate failing section only, ask user for tone preference |

## 8. Auto-routing from natural language

The plugin's skill triggers on natural-language requests via its frontmatter description (the keyword cues below are hints to Claude Code's skill-detection — they are **not** matched as literal regex by the routing logic itself).

**Skill description cues** (selection of trigger phrases included in the skill's YAML frontmatter):

```
"review X", "peer-review", "critique paper/manuscript",
"analyze codebase/repo/data/results", "build plot for", "make a figure",
"find papers on", "literature survey", "state of the art in", "latest research on",
"implement algorithm X", "write code for benchmark", "code up Y from scratch",
"hypothesize about", "what could explain", "research X", "investigate Y",
"study Z", "look at most advanced X and write code", "compare X vs Y experimentally"
```

**Phase −1 — intent classification** runs in the skill itself, using **Claude's reasoning over the user's request**. The classifier maps free-form text to one of the 12 named intents below. The keyword examples in the table are guidance, not regex matchers — the skill reads the request and reasons about which intent best fits.

| # | Named intent | Example trigger phrasings | Agents dispatched |
|---|---|---|---|
| 1 | review-only | "review X", "peer-review", "critique" | reviewer |
| 2 | analyze-codebase | "analyze codebase Y", "audit repo", "scan code" | codebase-scanner |
| 3 | analyze-data | "analyze results", "stats from results.csv" | plotter, meta-analyst |
| 4 | plot-only | "build plot for", "make figure", "visualize" | plotter |
| 5 | literature-only | "find papers", "state of the art", "latest research" | literature-searcher |
| 6 | code-only | "implement X", "write code for", "from scratch" | code-generator (+ experiment-runner if "and run/test") |
| 7 | hypothesis-only | "hypothesize", "what could explain" | ideator, hypothesizer (+ light literature-searcher) |
| 8 | full-pipeline | "research X", "investigate", "study", `/ai-scientist` | all 12 |
| 9 | compound: lit + code + experiment + plot | "look at advanced X and write code, then analyze" | literature-searcher, code-generator, experiment-runner, plotter |
| 10 | comparison | "compare X vs Y experimentally" | code-generator, experiment-runner, plotter, meta-analyst |
| 11 | manuscript-from-results | "write paper from <results-dir>" | manuscript-writer, citator, reviewer |
| 12 | ambiguous | (cannot classify) | none — surface AskUserQuestion to disambiguate |

**Self-consistent tool picking:** each agent's tool list is least-privilege (Section 5). When only Plotter runs, only Plotter's tools are active in the dispatched subagent — there is no global "all tools" surface.

**Override:** prefix with `/ai-scientist` or add `--full` to force the full pipeline. `--only <agent>` forces single-agent mode regardless of phrasing.

**Future work (not v1):** if classification quality proves insufficient in practice, promote Phase −1 from in-skill reasoning to a dedicated `router.md` agent.

## 9. Literature search upgrades

**Metadata cross-validation** (default `metadata_validation: "strict"`):

1. After the 6-source merge, for every paper with a DOI: query Crossref or OpenAlex to verify `title` + `first_author` + `year` match.
2. For papers without a DOI: attempt resolution via OpenAlex search by `title + first_author`.
3. On mismatch: prefer the OpenAlex/Crossref canonical record, downgrade the original to `metadata_confidence: "low"`, and log the discrepancy.
4. Records that fail validation 3 times are dropped.
5. All corrections + drops written to `<output-dir>/validation_log.json`.

**OpenAlex throttling:**

- Token-bucket rate limiter at default 5 req/s when `OPENALEX_EMAIL` is set (well under the 10 req/s polite cap).
- 1 req/s when email is unset.
- Exponential backoff on 429: 2s → 5s → 12s → escalate to Fixer.
- Configurable via `settings.literature.openalex_rate_limit_per_second`.

## 10. Manuscript output — LaTeX + Word + visual validation

**LaTeX templates** at `mcp/templates/latex/`:

| Template | Use case |
|---|---|
| `aiscientist-default.tex` | NeurIPS-style — default, general ML/CS |
| `overleaf-minimal.tex` | Clean single-column |
| `elsevier-cas-sc.tex` | Domain-journal style |
| `ieee-conference.tex` | Two-column engineering |
| `acm-sig.tex` | CS conferences |

**Word templates** at `mcp/templates/word/` (sourced from publicly shared author templates with permissive licenses; license verification is a planning task):

| Template | Use case |
|---|---|
| `arxiv-shared-1.docx` | arXiv-author shared template |
| `minimalist.docx` | A4 sans-serif, non-CS audiences |
| `two-column-academic.docx` | Letter, two-column |

**Generation pipeline:**

1. ManuscriptWriter writes LaTeX first (using chosen `.tex` template).
2. Convert to `.docx` via Pandoc: `pandoc manuscript.tex --reference-doc=mcp/templates/word/<chosen>.docx -o manuscript.docx`. Pandoc preserves equations (LaTeX math → Word equation objects), figures, tables, citations.
3. **Fallback:** if Pandoc is missing, the skill invokes the **anthropic-skills:docx** skill to construct the Word doc cell-by-cell from section subagent outputs.
4. **Last-resort:** if both Pandoc and the docx skill are unavailable, install script attempts `winget install pandoc` (Windows) and re-runs. If still unavailable, Word export is skipped with a clear message and `/ai-scientist-resume <job-id>` can be used after manual install.

**Visual validation pass (Phase 8.5):**

1. Skill renders both outputs to PNG: `pdftoppm -r 150 manuscript.pdf manuscript_page` (LaTeX) and `libreoffice --headless --convert-to pdf manuscript.docx && pdftoppm -r 150 manuscript.pdf word_page` (Word).
2. Skill inlines PNG paths into a Reviewer call. Reviewer's `Read` tool is multimodal — it sees the rendered pages.
3. Reviewer flags visual issues: overflowing tables, bad page breaks, missing figures, broken citations, unrendered math, ugly margins, font fallbacks.
4. High-severity issues route through the Fixer flow. Low-severity issues logged in `visual_review.json` and surfaced in the run summary.

## 11. Settings / tweaking surface

Hierarchy: plugin defaults < user `~/.claude/settings.json` < per-run CLI flags.

```jsonc
{
  "plugins": {
    "ai-scientist": {
      "agents": {
        "ideator":            { "model": "opus",   "thinking_budget": 48000 },
        "codebase_scanner":   { "model": "sonnet", "thinking_budget": 8000  },
        "literature_searcher":{ "model": "sonnet", "thinking_budget": 8000  },
        "hypothesizer":       { "model": "opus",   "thinking_budget": 64000 },
        "code_generator":     { "model": "opus",   "thinking_budget": 48000 },
        "experiment_runner":  { "model": "sonnet", "thinking_budget": 8000  },
        "plotter":            { "model": "sonnet", "thinking_budget": 8000  },
        "manuscript_writer":  { "model": "opus",   "thinking_budget": 48000 },
        "citator":            { "model": "sonnet", "thinking_budget": 8000  },
        "reviewer":           { "model": "opus",   "thinking_budget": 64000 },
        "meta_analyst":       { "model": "sonnet", "thinking_budget": 8000  },
        "fixer":              { "model": "sonnet", "thinking_budget": 16000 }
      },

      "interactivity": "checkpoints",
      "auto_fix_max_rounds": 3,
      "fixer_max_rounds_per_phase": 3,

      "phases": {
        "codebase_scan":       "auto",
        "novelty_check":       "on",
        "plot_aggregation":    "on",
        "citation_enrichment": { "enabled": true, "max_rounds": 5 },
        "self_review":         "on",
        "latex_compile":       "auto",
        "word_export":         "auto",
        "visual_validation":   "on",
        "knowledge_index":     "on",
        "meta_analysis":       "on"
      },

      "manuscript": {
        "latex_template":    "aiscientist-default",
        "word_template":     "arxiv-shared-1",
        "tone":              "technical",
        "citation_density":  "medium"
      },

      "literature": {
        "max_papers":              50,
        "year_floor":              2024,
        "fallback_year_floor":     2020,
        "min_unique_threshold":    15,
        "metadata_validation":     "strict",
        "openalex_rate_limit_per_second": 5,
        "sources": {
          "semantic_scholar": true,
          "openalex":         true,
          "arxiv":            true,
          "biorxiv":          true,
          "pubmed":           true,
          "consensus":        true,
          "annas_archive":    true
        }
      },

      "credentials": {
        "openalex_email":       "${env:OPENALEX_EMAIL}",
        "semantic_scholar_key": "${env:SEMANTIC_SCHOLAR_KEY}"
      },

      "storage": {
        "knowledge_root":         "~/.ai-scientist",
        "default_output_root":    "./ai-scientist-output",
        "retain_completed_jobs_days": 90
      },

      "experiment": {
        "timeout_seconds":               300,
        "venv_per_job":                  true,
        "max_dependency_install_attempts": 2
      }
    }
  }
}
```

A `settings.schema.json` ships alongside for editor linting and future Customize-form support.

**CLI flags** map 1-to-1 to settings keys:

```
/ai-scientist <topic>
  --domain ml|optimization|statistical|mathematical|computational_biology|software_engineering
  --output <dir>
  --codebase <path>
  --interactivity none|checkpoints|full
  --latex-template <name>
  --word-template <name>
  --reviewer-model opus|sonnet
  --hypothesizer-thinking 32000|48000|64000
  --no-word-export
  --no-novelty-check
  --max-papers 30
  --full                 # force full pipeline regardless of routing
  --only <agent>         # single-agent mode
```

CLI flags win over settings.json for that one run.

## 12. MCP server wiring

`mcp_server.py` and `lib/` are **copied** (not symlinked) into `mcp/` inside the plugin. The plugin's `.mcp.json`:

```jsonc
{
  "mcpServers": {
    "ai-scientist": {
      "command": "python",
      "args": ["${plugin_root}/mcp/server.py", "--mode", "stdio"],
      "env": {
        "AI_SCIENTIST_HOME": "${env:USERPROFILE}/.ai-scientist",
        "PYTHONPATH": "${plugin_root}/mcp/lib"
      }
    }
  }
}
```

The MCP reads/writes against `~/.ai-scientist/` for runtime data (knowledge.db, jobs.json) so existing data is preserved across plugin reinstalls/updates.

**Tools exposed** (preserved from current server):
- Job lifecycle: `start_research`, `get_status`, `get_output`, `list_jobs`, `list_templates`, `cancel_job`
- Knowledge: `search_knowledge_index`, `get_knowledge_details`, `query_knowledge`, `query_knowledge_graph`, `get_knowledge_stats`
- v2 helpers: `analyze_codebase`, `get_meta_analysis`, `get_what_works`, `run_meta_analysis`

## 13. Migration plan

`scripts/migrate-from-skill.ps1` runs once on first install:

1. Detect `~/.claude/skills/ai-scientist/SKILL.md`.
2. Move it to `~/.claude/backups/ai-scientist-skill-<timestamp>/SKILL.md`. Print backup path.
3. Leave `~/.ai-scientist/mcp_server.py` + `lib/` in place (untouched, available as fallback).
4. Verify plugin's `mcp/server.py` starts cleanly via `python mcp/server.py --selftest`.
5. Verify `~/.ai-scientist/knowledge.db` opens and has expected tables (`papers`, `hypotheses`, `triples`, `trajectories`).
6. Print migration receipt: backup path, knowledge stats (paper count, job count, DB size), and a smoke-test command.

`scripts/rollback.ps1` restores the backup and removes the marketplace entry. Knowledge data is untouched in either direction.

## 14. Validation strategy

Three layers, all runnable from `scripts/verify.ps1`:

**Static checks** (fast, no LLM):
- All 12 agent files parse (valid YAML frontmatter, required fields).
- `plugin.json` validates against Claude Code's plugin schema.
- `default-settings.json` validates against `settings.schema.json`.
- All slash command files parse.
- `.mcp.json` paths resolve.

**MCP smoke test:**
- Start MCP with `--selftest`; assert it initializes, exposes 14 expected tools, queries knowledge DB, exits 0.

**Routing tests** (cheap, no full pipeline):
- 12 fixture prompts (one per named intent in Section 8). Each verifies the skill picks the right agent set without dispatching them.
- Fixture file: `tests/routing-fixtures.json`.

**End-to-end smoke run** (gated behind `--e2e`):
- `/ai-scientist "linear regression on synthetic data" --domain statistical --interactivity none --no-word-export`.
- Expected: completes <5 min, produces `manuscript.tex`, `results.csv`, ≥4 figures, `review.json` with score ≥3.
- Asserts each agent ran with its configured model (parsed from telemetry).

**Visual validation regression** (manual, periodic):
- 3 reference manuscripts compiled (one per LaTeX template), 3 Word docs (one per Word template) — visual diff against committed PNG snapshots.

## 15. Open questions deferred to implementation

- Exact list of shared author Word templates and their licenses — to be hunted and verified during implementation (Plan task).
- Whether to fail-loud or fail-soft when `OPENALEX_EMAIL` is unset (current decision: fail-soft, drop to 1 req/s and warn once).
- Whether nested manuscript-section subagents should each get an individual model override in settings, or inherit from `manuscript_writer`. Default: inherit. Customization deferred to v1.1.
- Whether to ship a `claude-flow` style swarm-coordination MCP — not in v1.

## 16. Acceptance criteria

The plugin is considered complete when:

1. Plugin is installable via `/plugin marketplace add C:\Users\danil\OneDrive\Рабочий стол\MCPs\` and visible in **Customize**.
2. All 12 agents parse and dispatch with their pinned models (verified by routing tests).
3. `/ai-scientist <topic>` runs the full pipeline end-to-end on the synthetic-statistical smoke test.
4. Natural-language requests for each of the 12 named intents route to the correct agent subset.
5. Forced failure (e.g., bad import) triggers Fixer + AskUserQuestion flow; recovery succeeds on user pick.
6. Manuscript outputs to both `manuscript.tex` and `manuscript.docx`; visual validation pass produces `visual_review.json`.
7. `~/.ai-scientist/knowledge.db` is preserved through migration; existing 17+ jobs visible via `/ai-scientist-list`.
8. Settings overrides work for at least: agent model swap, thinking budget bump, phase disable, OpenAlex rate limit.
