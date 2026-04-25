# AI-Scientist Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce the existing `~/.claude/skills/ai-scientist/SKILL.md` + `~/.ai-scientist/mcp_server.py` as a first-class Claude Code plugin with 12 dedicated subagents (each with pinned model + thinking budget), Fixer-driven error recovery, dual LaTeX/Word output, visual validation, natural-language auto-routing, and full settings-based tweakability.

**Architecture:** Approach B — orchestrator skill owns deterministic file I/O, dependency installation, BibTeX dedup, and intent routing; 12 agent files own LLM-thinking work and are dispatched via `Task()`. MCP server + Python lib are bundled inside the plugin; runtime knowledge data stays at `~/.ai-scientist/` for survival across reinstalls.

**Tech Stack:** Claude Code plugin format (plugin.json + agents/ + skills/ + commands/ + .mcp.json), Python 3.11 + SQLite + ChromaDB for the MCP backend, Pandoc + LibreOffice for LaTeX/Word/PDF rendering, PowerShell scripts for install/migrate/verify on Windows.

**Spec:** `docs/specs/2026-04-25-ai-scientist-plugin-design.md`

**Plugin root:** `C:\Users\danil\OneDrive\Рабочий стол\MCPs\ai-scientist-plugin\` (referred to below as `<PLUGIN_ROOT>`).

**Marketplace root:** `C:\Users\danil\OneDrive\Рабочий стол\MCPs\` (parent dir; will host `marketplace.json`).

---

## File Structure (created across all tasks)

```
<PLUGIN_ROOT>\
├── .claude-plugin\
│   ├── plugin.json
│   └── marketplace.json                    (also copied to parent for install)
├── README.md
├── LICENSE
├── agents\
│   ├── ideator.md
│   ├── codebase-scanner.md
│   ├── literature-searcher.md
│   ├── hypothesizer.md
│   ├── code-generator.md
│   ├── experiment-runner.md
│   ├── plotter.md
│   ├── manuscript-writer.md
│   ├── citator.md
│   ├── reviewer.md
│   ├── meta-analyst.md
│   └── fixer.md
├── skills\ai-scientist\
│   ├── SKILL.md
│   ├── domain-templates.md
│   ├── academic-domains.md
│   ├── search-queries.md
│   └── routing-intents.md
├── commands\
│   ├── ai-scientist.md
│   ├── ai-scientist-list.md
│   ├── ai-scientist-output.md
│   ├── ai-scientist-query.md
│   ├── ai-scientist-meta.md
│   └── ai-scientist-resume.md
├── mcp\
│   ├── .mcp.json
│   ├── server.py
│   ├── requirements.txt
│   ├── lib\
│   │   ├── __init__.py
│   │   ├── knowledge_store.py
│   │   ├── chroma_store.py
│   │   ├── codebase_analyzer.py
│   │   ├── experiment_runner.py
│   │   ├── manuscript_coordinator.py
│   │   ├── meta_analyzer.py
│   │   └── sqlite_store.py
│   └── templates\
│       ├── latex\
│       │   ├── aiscientist-default.tex
│       │   ├── overleaf-minimal.tex
│       │   ├── elsevier-cas-sc.tex
│       │   ├── ieee-conference.tex
│       │   └── acm-sig.tex
│       └── word\
│           ├── arxiv-shared-1.docx
│           ├── minimalist.docx
│           ├── two-column-academic.docx
│           └── LICENSES.md
├── settings\
│   ├── default-settings.json
│   └── settings.schema.json
├── tests\
│   ├── routing-fixtures.json
│   ├── test_static_checks.py
│   ├── test_routing.py
│   └── test_mcp_smoke.py
├── docs\
│   ├── specs\2026-04-25-ai-scientist-plugin-design.md      (already exists)
│   └── plans\2026-04-25-ai-scientist-plugin-implementation.md  (this file)
└── scripts\
    ├── install.ps1
    ├── migrate-from-skill.ps1
    ├── rollback.ps1
    └── verify.ps1
```

**Runtime data (untouched, survives reinstalls):**
- `~/.ai-scientist/knowledge.db`
- `~/.ai-scientist/jobs.json`
- `~/.ai-scientist/trajectories.jsonl`
- `~/.ai-scientist/meta_analysis.json`
- `~/.ai-scientist/what_works.json`

---

# Phase A — Plugin scaffolding

## Task 1: Initialize git repository and write LICENSE

**Files:**
- Create: `<PLUGIN_ROOT>\LICENSE`
- Create: `<PLUGIN_ROOT>\.gitignore`

- [ ] **Step 1: Initialize git repo**

```bash
cd "C:\Users\danil\OneDrive\Рабочий стол\MCPs\ai-scientist-plugin"
git init
git config user.email "scienceboylovesyou@gmail.com"
git config user.name "scienceboylovesyou"
```

Expected: `Initialized empty Git repository in .../ai-scientist-plugin/.git/`

- [ ] **Step 2: Write LICENSE (MIT)**

Create `<PLUGIN_ROOT>\LICENSE` with the standard MIT text:

```
MIT License

Copyright (c) 2026 scienceboylovesyou

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Write .gitignore**

Create `<PLUGIN_ROOT>\.gitignore`:

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# OS
.DS_Store
Thumbs.db
desktop.ini

# Editor
.vscode/
.idea/

# Pipeline outputs (when running from plugin dir)
ai-scientist-output/

# Logs
*.log
```

- [ ] **Step 4: Commit**

```bash
git add LICENSE .gitignore
git commit -m "chore: initial commit with MIT license and gitignore"
```

Expected: `[main (root-commit) ...] chore: initial commit with MIT license and gitignore`

---

## Task 2: Write plugin.json manifest

**Files:**
- Create: `<PLUGIN_ROOT>\.claude-plugin\plugin.json`

- [ ] **Step 1: Create directory and write manifest**

Create `<PLUGIN_ROOT>\.claude-plugin\plugin.json`:

```json
{
  "name": "ai-scientist",
  "description": "Agentic AI-Scientist research pipeline. End-to-end scientific research with 12 specialized subagents (Ideator, Hypothesizer, CodeGenerator, ManuscriptWriter, Reviewer, etc.), each on a pinned model with extended thinking. Auto-routes natural-language requests (review/analyze/plot/code) to the smallest agent subset. Produces both LaTeX and Word manuscripts with visual validation.",
  "version": "1.0.0",
  "author": {
    "name": "scienceboylovesyou",
    "email": "scienceboylovesyou@gmail.com"
  },
  "license": "MIT",
  "keywords": [
    "research",
    "ai-scientist",
    "subagents",
    "scientific-writing",
    "literature-review",
    "experiment-automation",
    "peer-review"
  ]
}
```

- [ ] **Step 2: Validate JSON syntax**

Run: `python -c "import json; json.load(open(r'<PLUGIN_ROOT>\.claude-plugin\plugin.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: add plugin.json manifest"
```

---

## Task 3: Write marketplace.json and install copy

**Files:**
- Create: `<PLUGIN_ROOT>\.claude-plugin\marketplace.json`
- Create: `C:\Users\danil\OneDrive\Рабочий стол\MCPs\marketplace.json`

- [ ] **Step 1: Write marketplace.json inside plugin**

Create `<PLUGIN_ROOT>\.claude-plugin\marketplace.json`:

```json
{
  "name": "ai-scientist-local",
  "owner": {
    "name": "scienceboylovesyou",
    "email": "scienceboylovesyou@gmail.com"
  },
  "plugins": [
    {
      "name": "ai-scientist",
      "source": ".",
      "description": "Agentic AI-Scientist research pipeline plugin"
    }
  ]
}
```

- [ ] **Step 2: Copy to parent dir for `/plugin marketplace add`**

Run:
```bash
copy "<PLUGIN_ROOT>\.claude-plugin\marketplace.json" "C:\Users\danil\OneDrive\Рабочий стол\MCPs\marketplace.json"
```

Edit the parent copy so `source` points to the plugin subdir:

```json
{
  "name": "ai-scientist-local",
  "owner": {
    "name": "scienceboylovesyou",
    "email": "scienceboylovesyou@gmail.com"
  },
  "plugins": [
    {
      "name": "ai-scientist",
      "source": "./ai-scientist-plugin",
      "description": "Agentic AI-Scientist research pipeline plugin"
    }
  ]
}
```

- [ ] **Step 3: Validate both JSON files**

Run:
```bash
python -c "import json; json.load(open(r'<PLUGIN_ROOT>\.claude-plugin\marketplace.json')); json.load(open(r'C:\Users\danil\OneDrive\Рабочий стол\MCPs\marketplace.json'))"
```

Expected: no output, exit 0.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat: add marketplace.json for local marketplace registration"
```

(The parent-dir copy is intentionally outside the plugin repo.)

---

## Task 4: Create empty directory structure

**Files:**
- Create: all directories listed in the File Structure section above (use empty `.gitkeep` files where Git would otherwise drop them)

- [ ] **Step 1: Create all empty subdirectories**

Run from `<PLUGIN_ROOT>`:

```bash
mkdir -p agents
mkdir -p skills/ai-scientist
mkdir -p commands
mkdir -p mcp/lib
mkdir -p mcp/templates/latex
mkdir -p mcp/templates/word
mkdir -p settings
mkdir -p tests
mkdir -p scripts
```

- [ ] **Step 2: Verify**

Run: `find . -type d -not -path './.git*' | sort`
Expected output (subset, plus existing `docs/`):

```
.
./.claude-plugin
./agents
./commands
./docs
./docs/plans
./docs/specs
./mcp
./mcp/lib
./mcp/templates
./mcp/templates/latex
./mcp/templates/word
./scripts
./settings
./skills
./skills/ai-scientist
./tests
```

- [ ] **Step 3: No commit yet**

(Empty dirs aren't tracked. Subsequent tasks fill them and commit per-task.)

---

# Phase B — MCP server + Python lib relocation

## Task 5: Copy lib/ from `~/.ai-scientist/lib/` into `<PLUGIN_ROOT>\mcp\lib\`

**Files:**
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\__init__.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\knowledge_store.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\chroma_store.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\codebase_analyzer.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\experiment_runner.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\manuscript_coordinator.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\meta_analyzer.py`
- Create (copy): `<PLUGIN_ROOT>\mcp\lib\sqlite_store.py`

- [ ] **Step 1: Copy all 8 files**

```bash
copy "C:\Users\danil\.ai-scientist\lib\__init__.py" "<PLUGIN_ROOT>\mcp\lib\__init__.py"
copy "C:\Users\danil\.ai-scientist\lib\knowledge_store.py" "<PLUGIN_ROOT>\mcp\lib\knowledge_store.py"
copy "C:\Users\danil\.ai-scientist\lib\chroma_store.py" "<PLUGIN_ROOT>\mcp\lib\chroma_store.py"
copy "C:\Users\danil\.ai-scientist\lib\codebase_analyzer.py" "<PLUGIN_ROOT>\mcp\lib\codebase_analyzer.py"
copy "C:\Users\danil\.ai-scientist\lib\experiment_runner.py" "<PLUGIN_ROOT>\mcp\lib\experiment_runner.py"
copy "C:\Users\danil\.ai-scientist\lib\manuscript_coordinator.py" "<PLUGIN_ROOT>\mcp\lib\manuscript_coordinator.py"
copy "C:\Users\danil\.ai-scientist\lib\meta_analyzer.py" "<PLUGIN_ROOT>\mcp\lib\meta_analyzer.py"
copy "C:\Users\danil\.ai-scientist\lib\sqlite_store.py" "<PLUGIN_ROOT>\mcp\lib\sqlite_store.py"
```

- [ ] **Step 2: Verify each module imports cleanly**

Run from `<PLUGIN_ROOT>\mcp`:

```bash
python -c "import sys; sys.path.insert(0, r'<PLUGIN_ROOT>\mcp\lib'); import knowledge_store, chroma_store, codebase_analyzer, experiment_runner, manuscript_coordinator, meta_analyzer, sqlite_store; print('OK')"
```

Expected: `OK`. If any ImportError surfaces (e.g. missing dependency like `chromadb`), note it for `requirements.txt` (Task 7).

- [ ] **Step 3: Commit**

```bash
git add mcp/lib/
git commit -m "feat(mcp): bundle Python helper lib into plugin"
```

---

## Task 6: Refactor mcp_server.py and copy as `<PLUGIN_ROOT>\mcp\server.py`

**Files:**
- Create: `<PLUGIN_ROOT>\mcp\server.py` (copied from `~/.ai-scientist/mcp_server.py` with the changes below)

- [ ] **Step 1: Copy file**

```bash
copy "C:\Users\danil\.ai-scientist\mcp_server.py" "<PLUGIN_ROOT>\mcp\server.py"
```

- [ ] **Step 2: Update import-path resolution at top of `server.py`**

Replace lines 28–30 (the original `sys.path.insert`):

```python
# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
```

with:

```python
# Add bundled lib/ to path. Plugin layout: <plugin_root>/mcp/lib
sys.path.insert(0, str(Path(__file__).parent / "lib"))
```

- [ ] **Step 3: Update BASE_DIR resolution**

Replace line 34:

```python
BASE_DIR = Path.home() / ".ai-scientist"
```

with:

```python
# Runtime data root. Defaults to ~/.ai-scientist/ but is overridable via
# AI_SCIENTIST_HOME env var (set by .mcp.json). This keeps user data alive
# across plugin reinstalls.
BASE_DIR = Path(os.environ.get("AI_SCIENTIST_HOME", str(Path.home() / ".ai-scientist")))
```

- [ ] **Step 4: Add `--selftest` flag in the argparse block**

In the bottom `if __name__ == "__main__":` block, add a new arg:

```python
parser.add_argument("--selftest", action="store_true",
                    help="Run a non-LLM smoke check: open DB, list tools, exit 0/1")
```

And add a handler before the `args.mode` switch:

```python
if args.selftest:
    try:
        store = KnowledgeStore()
        stats = store.get_stats()
        store.close()
        expected_tools = {
            "start_research", "get_status", "get_output", "list_jobs",
            "list_templates", "cancel_job", "query_knowledge",
            "search_knowledge_index", "get_knowledge_details",
            "query_knowledge_graph", "get_knowledge_stats",
            "analyze_codebase", "get_meta_analysis", "get_what_works",
            "run_meta_analysis"
        }
        # Tool list comes from the dispatch table in handle_request — verify
        # by inspection: dump source and grep for tool_name == ...
        print(f"selftest: BASE_DIR={BASE_DIR}", file=sys.stderr)
        print(f"selftest: knowledge_store backend={stats.get('backend')}", file=sys.stderr)
        print(f"selftest: papers_count={stats.get('papers_count', 0)}", file=sys.stderr)
        print(f"selftest: OK", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"selftest: FAILED — {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 5: Add the 4 v2-helper tools to the dispatch table**

In `handle_request()` after the existing `elif tool_name == "get_knowledge_stats":` branch, insert these 4 branches before the final `else`:

```python
elif tool_name == "analyze_codebase":
    from codebase_analyzer import analyze
    result = analyze(
        codebase_path=tool_args.get("codebase_path", ""),
        output_file=tool_args.get("output_file")
    )
elif tool_name == "get_meta_analysis":
    store = KnowledgeStore()
    result = store.read_meta_analysis() or {}
    store.close()
elif tool_name == "get_what_works":
    store = KnowledgeStore()
    result = store.read_what_works() or {}
    store.close()
elif tool_name == "run_meta_analysis":
    from meta_analyzer import MetaAnalyzer
    analyzer = MetaAnalyzer(BASE_DIR)
    result = analyzer.run_full_analysis()
```

(Verify the `analyze` function exists in `codebase_analyzer.py` — if it has a different entry-point name like `analyze_codebase`, adjust the import accordingly. Inspect lib first: `grep -n "^def " <PLUGIN_ROOT>/mcp/lib/codebase_analyzer.py`.)

- [ ] **Step 6: Run the selftest**

```bash
python "<PLUGIN_ROOT>\mcp\server.py" --selftest
```

Expected stderr ending with `selftest: OK`, exit 0.

- [ ] **Step 7: Commit**

```bash
git add mcp/server.py
git commit -m "feat(mcp): plugin-aware server.py with --selftest and v2 helper tools"
```

---

## Task 7: Write `mcp/requirements.txt` and `mcp/.mcp.json`

**Files:**
- Create: `<PLUGIN_ROOT>\mcp\requirements.txt`
- Create: `<PLUGIN_ROOT>\mcp\.mcp.json`

- [ ] **Step 1: Write requirements.txt**

Inspect lib imports first:

```bash
grep -h "^import\|^from" <PLUGIN_ROOT>/mcp/lib/*.py | sort -u
```

Compose `requirements.txt` based on the imports + standard ai-scientist deps:

```
chromadb>=0.4.22
sentence-transformers>=2.5.0
numpy>=1.26
pandas>=2.0
scipy>=1.11
matplotlib>=3.8
requests>=2.31
```

(Add any extras revealed by the grep that aren't stdlib.)

- [ ] **Step 2: Write `.mcp.json`**

Create `<PLUGIN_ROOT>\mcp\.mcp.json`:

```json
{
  "mcpServers": {
    "ai-scientist": {
      "command": "python",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/mcp/server.py",
        "--mode",
        "stdio"
      ],
      "env": {
        "AI_SCIENTIST_HOME": "${env:USERPROFILE}/.ai-scientist",
        "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}/mcp/lib"
      }
    }
  }
}
```

(Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` to the plugin's install path.)

- [ ] **Step 3: Validate JSON**

```bash
python -c "import json; json.load(open(r'<PLUGIN_ROOT>\mcp\.mcp.json'))"
```

Expected: no output, exit 0.

- [ ] **Step 4: Commit**

```bash
git add mcp/requirements.txt mcp/.mcp.json
git commit -m "feat(mcp): add requirements and .mcp.json server registration"
```

---

# Phase C — Skill core files

## Task 8: Author `skills/ai-scientist/domain-templates.md`

**Files:**
- Create: `<PLUGIN_ROOT>\skills\ai-scientist\domain-templates.md`

- [ ] **Step 1: Write file**

Extract the "DOMAIN TEMPLATES" section verbatim from the original `~/.claude/skills/ai-scientist/SKILL.md` (lines ~213–247) into a standalone reference, lightly reformatted as a table for compactness:

```markdown
# Domain Templates

The orchestrator selects one template based on the `--domain` flag. Each defines `preferred_libraries`, `experiment_type`, `evaluation_metric`, and any extra manuscript sections.

| Domain | Libraries | Experiment type | Metric | Extra sections |
|---|---|---|---|---|
| ml | torch, torchvision, numpy, matplotlib, scikit-learn, einops | deep_learning_benchmark | validation_accuracy_and_loss | Related Work, Experiments |
| optimization | scipy, cvxpy, pulp, pyomo, numpy | optimization_benchmark | objective_value_and_solve_time | — |
| statistical | scipy, statsmodels, pingouin, numpy, pandas, matplotlib, seaborn | statistical_analysis | p_value_effect_size_and_confidence_interval | Related Work, Statistical Analysis |
| mathematical | sympy, scipy, numpy, matplotlib | mathematical_modeling | symbolic_solution_and_numerical_error | — |
| computational_biology | biopython, numpy, scipy, matplotlib, networkx | bioinformatics_analysis | alignment_score_and_structure_rmsd | Structure Prediction, Machine Learning for Design |
| software_engineering | pytest, hypothesis, black, mypy, pylint, numpy | software_benchmark | performance_and_correctness | Architecture, Implementation Details, Benchmarks |
```

- [ ] **Step 2: Commit**

```bash
git add skills/ai-scientist/domain-templates.md
git commit -m "feat(skill): extract domain templates reference"
```

---

## Task 9: Author `skills/ai-scientist/academic-domains.md`

**Files:**
- Create: `<PLUGIN_ROOT>\skills\ai-scientist\academic-domains.md`

- [ ] **Step 1: Write file**

Copy verbatim the "ACADEMIC DOMAINS REFERENCE" section from original SKILL.md (lines ~146–177) into:

```markdown
# Academic Domains Reference

Trusted publisher allowlist for filtering literature search results. Reject any URL whose host doesn't match one of these.

## Preprint Servers
arxiv.org, biorxiv.org, medrxiv.org, chemrxiv.org, ssrn.com, preprints.org, eartharxiv.org, engrxiv.org, osf.io/preprints, techrxiv.org, researchsquare.com, authorea.com, zenodo.org

## Major Open-Access Publishers
mdpi.com, frontiersin.org, plos.org, hindawi.com, biomedcentral.com, springeropen.com, peerj.com, elifesciences.org, royalsocietypublishing.org, pensoft.net, copernicus.org, jmir.org, f1000research.com, scipost.org

## Major Subscription/Hybrid Publishers
nature.com, science.org, cell.com, sciencedirect.com, springer.com, link.springer.com, wiley.com, onlinelibrary.wiley.com, tandfonline.com, sagepub.com, oup.com, academic.oup.com, cambridge.org, elsevier.com, degruyter.com, karger.com, thieme-connect.com, iucr.org, benthamscience.com, ingentaconnect.com, worldscientific.com, iospress.com, nowpublishers.com

## Medical / Life Sciences / Veterinary / Agriculture
pubmed.ncbi.nlm.nih.gov, ncbi.nlm.nih.gov, pmc.ncbi.nlm.nih.gov, bmj.com, jamanetwork.com, nejm.org, thelancet.com, embopress.org, asm.org, ashpublications.org, ahajournals.org, atsjournals.org, gastrojournal.org, aac.asm.org, journals.lww.com, avmajournals.avma.org, veterinaryrecord.bmj.com, journals.sagepub.com/home/vet, academic.oup.com/jas, journalofdairyscience.org, animalsciencepublications.org, sciencedirect.com/journal/livestock-science, sciencedirect.com/journal/animal-feed-science-and-technology

## Engineering / CS / Physics / Mathematics
ieeexplore.ieee.org, dl.acm.org, aip.org, aps.org, iopscience.iop.org, siam.org, asme.org, asce.org, spie.org, osapublishing.org, optica.org, ams.org, msp.org, projecteuclid.org, epj.org, epljournal.org

## Chemistry / Materials / Environmental
acs.org, pubs.acs.org, rsc.org, pubs.rsc.org, chemeurj.org, chemistry-europe.onlinelibrary.wiley.com, journals.iucr.org, materialstoday.com, mrs.org, ehp.niehs.nih.gov, setac.onlinelibrary.wiley.com

## Earth / Geo / Ecology
agupubs.onlinelibrary.wiley.com, geoscienceworld.org, esajournals.onlinelibrary.wiley.com, int-res.com, bioone.org

## Social Sciences / Economics / Humanities
jstor.org, nber.org, repec.org, econpapers.repec.org, journals.uchicago.edu, muse.jhu.edu

## Aggregators / Indexes / Repositories
doi.org, semanticscholar.org, openalex.org, crossref.org, dimensions.ai, lens.org, core.ac.uk, annualreviews.org, europepmc.org, base-search.net, fatcat.wiki, unpaywall.org
```

(Note: dropped `sci-hub.se` from the original list to keep the plugin distribution-friendly.)

- [ ] **Step 2: Commit**

```bash
git add skills/ai-scientist/academic-domains.md
git commit -m "feat(skill): extract academic domains allowlist"
```

---

## Task 10: Author `skills/ai-scientist/search-queries.md`

**Files:**
- Create: `<PLUGIN_ROOT>\skills\ai-scientist\search-queries.md`

- [ ] **Step 1: Write file**

```markdown
# Search Query Strategy

For Phase 1 (Literature Search), the orchestrator constructs **8 queries** from the topic and dispatches them across all enabled sources.

## Query template

Given the user's topic `<core>` (truncated to first 150 chars):

| # | Query |
|---|---|
| Q1 | `<core>` |
| Q2 | `<core>` + " computational design" |
| Q3 | `<core>` + " deep learning" |
| Q4 | `<core>` + " structure prediction" |
| Q5 | `<core>` + " machine learning <domain>" |
| Q6 | `<core>` + " review 2025" |
| Q7 | `<core>` + " benchmark dataset" |
| Q8 | `<core>` + " therapeutic applications" |

(For non-bio domains, replace Q4/Q8 with domain-appropriate variants — e.g., `<core>` + " convergence analysis" for `mathematical`, `<core>` + " profiling benchmark" for `software_engineering`.)

## Prior-success queries

Before dispatching, the orchestrator reads `~/.ai-scientist/trajectories.jsonl` and extracts queries from previous successful runs on similar topics (EvolveR recall). These are appended to the 8 base queries, deduplicated.

## Per-source query budget

| Source | Queries used | Notes |
|---|---|---|
| Semantic Scholar | All 8 | If API key set; else 0 (key required for `/search`). |
| OpenAlex | All 8 | Primary source. Throttled — see `literature.openalex_rate_limit_per_second`. |
| arXiv | 2–4 | Topic + domain-specific. |
| bioRxiv | All 8 | Only if `domain == computational_biology`. |
| PubMed | 4 | Always except for `mathematical`/`statistical` domains. |
| Consensus | 2–3 | Rate-limited; main + comparison + review. |
| Anna's Archive | 1–2 | Foundational reviews + textbooks. |

## Fallback widening

If after merge+dedup the result count is below `literature.min_unique_threshold` (default 15):

1. Widen year floor from `literature.year_floor` (default 2024) to `literature.fallback_year_floor` (default 2020).
2. Re-query Semantic Scholar + OpenAlex with broader queries: just `<core>`, `<core>` + " methods", `<core>` + " pipeline software".
3. Last resort: `WebSearch` for recent reviews, then verify each result against `academic-domains.md`.

**Never fabricate metadata.** If a source is sparse, the orchestrator reports honestly.
```

- [ ] **Step 2: Commit**

```bash
git add skills/ai-scientist/search-queries.md
git commit -m "feat(skill): document literature search query strategy"
```

---

## Task 11: Author `skills/ai-scientist/routing-intents.md`

**Files:**
- Create: `<PLUGIN_ROOT>\skills\ai-scientist\routing-intents.md`

- [ ] **Step 1: Write file**

```markdown
# Routing Intents

The orchestrator's Phase −1 (intent classification) routes a user's natural-language request to one of these 12 named intents using **Claude's reasoning** (not literal regex). The example phrasings below are guidance, not matchers.

When ambiguous, surface `AskUserQuestion` to disambiguate.

## Intent table

| # | Name | Example phrasings | Agents dispatched | Required inputs |
|---|---|---|---|---|
| 1 | review-only | "review X", "peer-review", "critique my paper" | reviewer | path/url to manuscript |
| 2 | analyze-codebase | "analyze codebase", "audit repo Y", "scan code" | codebase-scanner | --codebase path |
| 3 | analyze-data | "analyze results", "stats from results.csv" | plotter, meta-analyst | data path |
| 4 | plot-only | "build plot for", "make figure", "visualize Z" | plotter | data path |
| 5 | literature-only | "find papers", "state of the art", "latest research" | literature-searcher | topic |
| 6 | code-only | "implement X", "write code for", "code Y from scratch" | code-generator (+ experiment-runner if "and run") | spec or topic |
| 7 | hypothesis-only | "hypothesize", "what could explain", "theory for" | ideator, hypothesizer (+ light literature-searcher) | topic |
| 8 | full-pipeline | "research X", "investigate", "study", `/ai-scientist <topic>` | all 12 | topic + domain |
| 9 | compound-lit-code-exp | "look at advanced X and write code, then analyze" | literature-searcher, code-generator, experiment-runner, plotter | topic |
| 10 | comparison | "compare X vs Y experimentally" | code-generator, experiment-runner, plotter, meta-analyst | X, Y |
| 11 | manuscript-from-results | "write paper from <results-dir>" | manuscript-writer, citator, reviewer | results dir |
| 12 | ambiguous | (cannot classify) | none — surface AskUserQuestion | — |

## Disambiguation rules

- If user says "analyze X" with no qualifier and X is a path: prefer **codebase-scanner** if X looks like a repo (presence of `.git`, `package.json`, `pyproject.toml`); else prefer **plotter + meta-analyst** if X is a CSV/JSON/NPY; else ask.
- If user says "review" without a target: ask for the manuscript path.
- If user provides a topic + "and run code": route to compound (literature → codegen → experiment → plot).
- If user provides `/ai-scientist` explicitly OR `--full`: always route to full-pipeline regardless of phrasing.

## Override flags

- `--full` → force full-pipeline (overrides any natural-language intent).
- `--only <agent>` → single-agent mode. Skip all other agents. The agent's required inputs become mandatory CLI flags.
- `--skip <agent1,agent2,...>` → force-skip listed agents in any pipeline.

## Tool minimization

When a partial intent is selected, only the listed agents' tools are active. The orchestrator never grants tool access beyond what the dispatched agents declare in their frontmatter.
```

- [ ] **Step 2: Commit**

```bash
git add skills/ai-scientist/routing-intents.md
git commit -m "feat(skill): document 12 routing intents and disambiguation rules"
```

---

## Task 12: Author the main `skills/ai-scientist/SKILL.md` orchestrator

**Files:**
- Create: `<PLUGIN_ROOT>\skills\ai-scientist\SKILL.md`

This is the largest single file in the plugin. It replaces the original 1076-line skill with a slimmer (~600-line) version that delegates thinking to agents but keeps deterministic plumbing.

- [ ] **Step 1: Write the file**

Create `<PLUGIN_ROOT>\skills\ai-scientist\SKILL.md` with the structure below. Reuse phase descriptions verbatim from the original SKILL.md where unchanged; replace inline subagent prompts with `Task()` dispatch directives.

Key sections required (in order):

```markdown
---
name: ai-scientist
description: >
  Use for any scientific research task — full or partial pipelines.
  Triggers on: "review X", "peer-review", "critique paper/manuscript",
  "analyze codebase/repo/data/results", "build plot for", "make a figure",
  "find papers on", "literature survey", "state of the art in", "latest research on",
  "implement algorithm X", "write code for benchmark", "code up Y from scratch",
  "hypothesize about", "what could explain", "research X", "investigate Y",
  "study Z", "look at most advanced X and write code", "compare X vs Y experimentally".
  Routes to a tailored subset of 12 dedicated subagents based on intent — not the full pipeline by default.
---

# AI-Scientist Orchestrator (Plugin v1.0)

You are the AI-Scientist orchestrator. You own deterministic plumbing — file I/O, dependency installation, BibTeX dedup, knowledge indexing — and dispatch all LLM-thinking work to 12 specialized subagents via `Task()`.

## Reference files (read on demand)
- `domain-templates.md` — 6 domain configs (libs/metrics/extra sections)
- `academic-domains.md` — trusted publisher allowlist
- `search-queries.md` — 8-query strategy + per-source budget + fallback rules
- `routing-intents.md` — 12 named intents + dispatch tables

## Phase −1: Intent classification

When invoked WITHOUT an explicit slash command (i.e., on natural-language requests), classify the user's request into one of the 12 intents in `routing-intents.md` using your own reasoning. Pick the smallest agent subset.

1. Read the user's request.
2. Map it to an intent (NOT regex — reason about it).
3. If ambiguous, use `AskUserQuestion` to disambiguate (offer the 2–3 most likely intents as options).
4. If `/ai-scientist` was invoked OR `--full` flag present: skip classification, route to full-pipeline (Intent #8, all 12 agents).
5. If `--only <agent>` flag present: dispatch only that agent.

Required inputs are listed in `routing-intents.md`. If missing, ask once.

## Phase 0: Initialization
[For full-pipeline only. For partial intents, jump to the relevant phase.]

1. Parse args: topic, domain, output dir, optional codebase path.
2. Generate job ID: 8-char random hex.
3. Create output dir: `<output-dir>/`.
4. Write `config.json` (job_id, topic, domain, codebase_path, created_at, preferred_libraries, experiment_type, evaluation_metric, python_version, pip_path, venv_path).
5. **Recall prior knowledge**: call `mcp__ai-scientist__search_knowledge_index(query=topic, limit=20)`, then `get_knowledge_details(ids=[...])` for top hits. Also `get_meta_analysis()` and `get_what_works()`. Report counts and reusable queries to user.
6. **Create venv**: `cd <output-dir> && python -m venv .venv && .venv\Scripts\activate && pip install --upgrade pip`.

## Phase 0.5: Ideation
Dispatch `Task(subagent_type="ai-scientist-ideator", prompt=...)`. Inline:
- Topic, domain, codebase path (if any)
- Prior knowledge summary (top 3 hits, meta-analysis recommendations)
Expect: JSON content for `idea.json`. Write to `<output-dir>/idea.json`.

[INTERACTIVITY: if settings.interactivity ≥ "checkpoints", let the Ideator AskUserQuestion if the structured idea matches user intent.]

## Phase 0.75: Codebase scan (optional)
If `--codebase <path>` provided, dispatch `Task(subagent_type="ai-scientist-codebase-scanner", ...)`. Inline path. Expect JSON for `codebase_analysis.json`. Write to disk.

## Phase 1: Literature search
Dispatch `Task(subagent_type="ai-scientist-literature-searcher", ...)`. Inline:
- Topic + 8 queries from `search-queries.md` template
- Domain (for source selection)
- Prior successful queries from trajectories.jsonl
- Throttle config (rate_limit_per_second from settings)
Expect: deduplicated paper list as JSON, with metadata-validation outcomes.

After return:
1. Filter against `academic-domains.md` allowlist.
2. Apply metadata cross-validation if `metadata_validation: strict`.
3. Write `paper_list.json`, `references.bib`, `validation_log.json`.

## Phase 2: Hypothesis
Read paper_list (first 10 papers compact), codebase_analysis.json, idea.json, prior hypotheses (via MCP), meta_analysis.json. Inline into `Task(subagent_type="ai-scientist-hypothesizer", ...)`. Expect: hypothesis.md content + equations.txt content.

## Phase 3: Codegen
Read hypothesis.md, config.json, codebase_analysis.json. Dispatch `Task(subagent_type="ai-scientist-code-generator", ...)`. Expect: experiment.py + requirements.txt content.

## Phase 4: Experiment
Dispatch `Task(subagent_type="ai-scientist-experiment-runner", ...)`. Inline:
- Path to output dir (it has Bash; will install deps and run)
- Auto-fix budget (default 3 rounds)
- Timeout (default 300s)
Expect: structured run report (exit codes, stdout/stderr summary, fix log).

[ON ERROR: trigger Fixer flow per Phase F.]

## Phase 5.5: Plot aggregation
Dispatch `Task(subagent_type="ai-scientist-plotter", ...)`. Inline output dir path, results.csv summary, list of .npy files. Expect: aggregator script + run summary.

## Phase 5: Manuscript
Read paper_list (first 30), references.bib, hypothesis.md (first 400 chars), experiment_stdout.txt (first 500 chars), results.csv summary, codebase_analysis.json, config.json.

Build coordination plan (citation budget, shared facts, figure references, BibTeX assignment).

Dispatch `Task(subagent_type="ai-scientist-manuscript-writer", ...)` — it will internally Task() 6 section subagents in parallel. Expect: assembled manuscript.tex.

Run consistency checks (cite-key existence, figure refs, contradictions, abstract↔results, no placeholders).

## Phase 6: Citation enrichment
Dispatch `Task(subagent_type="ai-scientist-citator", ...)`. Up to 5 rounds. Expect: updated references.bib.

## Phase 7: Self-review
Dispatch `Task(subagent_type="ai-scientist-reviewer", ...)`. Expect: review.json + manuscript_v2.tex (if Actionable_Fixes non-empty).

## Phase 8: LaTeX compile
Bash: `cd <output-dir> && pdflatex -interaction=nonstopmode manuscript.tex && bibtex manuscript && pdflatex ... && pdflatex ...`. On error → Fixer.

## Phase 8.25: Word export
1. Detect Pandoc: `where pandoc`.
2. If found: `pandoc manuscript.tex --reference-doc=<plugin>/mcp/templates/word/<chosen>.docx -o manuscript.docx`.
3. If not: invoke `Skill(skill="anthropic-skills:docx", ...)` with section content.
4. If both fail: skip with logged warning, allow `/ai-scientist-resume` after install.

## Phase 8.5: Visual validation
1. Render: `pdftoppm -r 150 manuscript.pdf manuscript_page` and `libreoffice --headless --convert-to pdf manuscript.docx && pdftoppm ...`.
2. Re-dispatch Reviewer with PNG paths inlined. Reviewer's Read is multimodal.
3. Write `visual_review.json`. High-severity → Fixer flow.

## Phase 9: Knowledge indexing
Direct MCP calls (no agent):
- `mcp__ai-scientist__index_papers(...)` (or write to `~/.ai-scientist/knowledge/papers.jsonl` directly)
- index hypothesis with outcome metadata
- index benchmark results
- index claims (abstract excerpt)
- add knowledge graph triples
- log trajectory
- update `~/.ai-scientist/jobs.json`

## Phase 10: Meta-analysis
Direct MCP: `mcp__ai-scientist__run_meta_analysis()`. (Or dispatch ai-scientist-meta-analyst for richer narrative.)

## Phase F: Fixer flow (on any phase failure or malformed agent output)
1. Capture failure context: phase, error class, stderr, current state.
2. Dispatch `Task(subagent_type="ai-scientist-fixer", ...)`. Expect: 2–4 fix options.
3. Surface to user via `AskUserQuestion`.
4. Apply pick → re-dispatch original agent.
5. Up to `fixer_max_rounds_per_phase` rounds. After exhaustion: full state dump + escalation prompt.

## Listing/query/output/meta commands

(Same as original SKILL.md sections "LISTING JOBS", "QUERYING KNOWLEDGE", "GETTING JOB OUTPUT", "META-ANALYSIS VIEW" — preserved verbatim with MCP tool calls.)

## Orchestration rules

1. Parallelism only inside literature-searcher and manuscript-writer (nested orchestrators).
2. Error handling per Phase F. NEVER silently proceed with empty/missing artifacts.
3. Progress reporting: print `[AI-Scientist v1.0] Phase X: <name> - <summary>` after each phase.
4. Subagent prompts MUST include all data (subagents can't read parent context).
5. No fabrication: honest reporting of failures.
6. Dependency-first: install requirements.txt before running experiment.py.
```

- [ ] **Step 2: Validate frontmatter parses**

Run:

```python
python -c "import yaml; doc=open(r'<PLUGIN_ROOT>\skills\ai-scientist\SKILL.md').read(); fm=doc.split('---')[1]; print(yaml.safe_load(fm))"
```

Expected: dict with `name`, `description` keys, no error.

- [ ] **Step 3: Commit**

```bash
git add skills/ai-scientist/SKILL.md
git commit -m "feat(skill): orchestrator SKILL.md with 12-agent dispatch + Fixer flow"
```

---

# Phase D — Agent files

## Task 13: Write static-test for agent file parsing

**Files:**
- Create: `<PLUGIN_ROOT>\tests\test_static_checks.py`

- [ ] **Step 1: Write the failing test**

```python
"""Static checks: every agent file has required frontmatter fields."""
import re
from pathlib import Path

import pytest
import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PLUGIN_ROOT / "agents"

EXPECTED_AGENTS = {
    "ideator", "codebase-scanner", "literature-searcher",
    "hypothesizer", "code-generator", "experiment-runner",
    "plotter", "manuscript-writer", "citator", "reviewer",
    "meta-analyst", "fixer",
}

REQUIRED_FRONTMATTER_KEYS = {"name", "description", "model", "thinking", "tools"}
ALLOWED_MODELS = {"opus", "sonnet", "haiku", "inherit"}


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        raise AssertionError(f"{path.name}: no YAML frontmatter")
    return yaml.safe_load(m.group(1))


def test_all_expected_agents_exist():
    found = {p.stem for p in AGENTS_DIR.glob("*.md")}
    missing = EXPECTED_AGENTS - found
    extra = found - EXPECTED_AGENTS
    assert not missing, f"missing agent files: {missing}"
    assert not extra, f"unexpected agent files: {extra}"


@pytest.mark.parametrize("agent_name", sorted(EXPECTED_AGENTS))
def test_agent_has_required_frontmatter(agent_name):
    fm = parse_frontmatter(AGENTS_DIR / f"{agent_name}.md")
    missing = REQUIRED_FRONTMATTER_KEYS - set(fm.keys())
    assert not missing, f"{agent_name}.md missing frontmatter keys: {missing}"


@pytest.mark.parametrize("agent_name", sorted(EXPECTED_AGENTS))
def test_agent_model_valid(agent_name):
    fm = parse_frontmatter(AGENTS_DIR / f"{agent_name}.md")
    assert fm["model"] in ALLOWED_MODELS, f"{agent_name}.md: invalid model {fm['model']!r}"


@pytest.mark.parametrize("agent_name", sorted(EXPECTED_AGENTS))
def test_agent_thinking_block(agent_name):
    fm = parse_frontmatter(AGENTS_DIR / f"{agent_name}.md")
    thinking = fm["thinking"]
    assert isinstance(thinking, dict), f"{agent_name}.md: thinking must be dict"
    assert "enabled" in thinking and "budget_tokens" in thinking, \
        f"{agent_name}.md: thinking needs enabled+budget_tokens"
    assert isinstance(thinking["budget_tokens"], int), \
        f"{agent_name}.md: budget_tokens must be int"
    assert 0 <= thinking["budget_tokens"] <= 128000, \
        f"{agent_name}.md: budget_tokens out of range"


@pytest.mark.parametrize("agent_name", sorted(EXPECTED_AGENTS))
def test_agent_tools_list(agent_name):
    fm = parse_frontmatter(AGENTS_DIR / f"{agent_name}.md")
    tools = fm["tools"]
    assert isinstance(tools, list) and len(tools) > 0, \
        f"{agent_name}.md: tools must be non-empty list"
```

- [ ] **Step 2: Run test, expect failure**

```bash
cd <PLUGIN_ROOT> && pytest tests/test_static_checks.py -v
```

Expected: `test_all_expected_agents_exist` FAILS with "missing agent files: {'ideator', ...}". This is correct — agents don't exist yet.

- [ ] **Step 3: Commit**

```bash
git add tests/test_static_checks.py
git commit -m "test: static checks for agent frontmatter"
```

---

## Task 14: Author `agents/ideator.md`

**Files:**
- Create: `<PLUGIN_ROOT>\agents\ideator.md`

- [ ] **Step 1: Write file**

```markdown
---
name: ai-scientist-ideator
description: Generates a structured research idea (Name, Title, Hypothesis, Related Work, Abstract, Experiments, Risks) with novelty check via OpenAlex/Semantic Scholar. Reads prior meta-analysis to avoid re-treading failed approaches.
model: opus
thinking:
  enabled: true
  budget_tokens: 48000
tools:
  - WebFetch
  - Read
  - AskUserQuestion
  - mcp__ai-scientist__search_knowledge_index
  - mcp__ai-scientist__get_knowledge_details
  - mcp__ai-scientist__get_meta_analysis
  - mcp__ai-scientist__get_what_works
---

# Ideator

You produce a single structured research idea grounded in prior knowledge and a novelty check.

## Inputs (inlined by orchestrator)

- `<input name="topic">` — raw research question
- `<input name="domain">` — one of {ml, optimization, statistical, mathematical, computational_biology, software_engineering}
- `<input name="codebase_summary">` — optional, from codebase-scanner
- `<input name="prior_meta">` — output of get_meta_analysis() and get_what_works()

## Steps

1. **Recall**: call `mcp__ai-scientist__search_knowledge_index(query=topic, limit=10)`. Note prior hypothesis-similarity.
2. **Generate structured idea** with these exact fields:
   - `Name`: lowercase_underscored
   - `Title`: paper-style
   - `Short_Hypothesis`: 1–2 sentences
   - `Related_Work`: how it differs
   - `Abstract`: ~250 words
   - `Experiments`: list with metric per experiment
   - `Risks`: honest list
   - `Self_Learning_Context`: extracted insights from prior_meta
3. **Novelty check**: WebFetch OpenAlex `https://api.openalex.org/works?search=<hypothesis-keywords>&per-page=10`. If 3+ very-similar works exist, refine the angle.
4. **Reflection**: re-read your own idea. Confirm hypothesis is testable in <5 min Python. Confirm experiments are feasible. Adjust if not.
5. **[Checkpoint]**: if interactivity is "checkpoints" or "full" (passed in inputs), use `AskUserQuestion` to ask the user whether the idea matches their intent or wants pivot.

## Output

Return ONLY a JSON object wrapped in `<output name="idea_json">...</output>` tags. No prose outside the tag.

```json
{
  "Name": "...",
  "Title": "...",
  "Short_Hypothesis": "...",
  "Related_Work": "...",
  "Abstract": "...",
  "Experiments": [{"name": "...", "metric": "..."}],
  "Risks": ["..."],
  "Self_Learning_Context": "...",
  "Novelty_Check": {"queries_run": [...], "similar_works_found": N, "refinement_applied": "..."}
}
```
```

- [ ] **Step 2: Run static test, expect 11 of 12 still failing**

```bash
pytest tests/test_static_checks.py::test_agent_has_required_frontmatter -v
```

Expected: `[ideator]` PASSES, others FAIL.

- [ ] **Step 3: Commit**

```bash
git add agents/ideator.md
git commit -m "feat(agents): ideator (opus 48k)"
```

---

## Tasks 15–24: Author the remaining 11 agent files

Each task is structurally identical to Task 14. For brevity, each task below specifies file path + frontmatter + the agent-specific body. Steps for every task: write → run static test → commit.

### Task 15: `agents/codebase-scanner.md`

```markdown
---
name: ai-scientist-codebase-scanner
description: Scans a target codebase to extract entry points, modules, dependencies, key patterns, and extension points. Emits structured codebase_analysis.json. Triggered when user provides --codebase or asks to analyze/audit a repo.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
tools:
  - Glob
  - Grep
  - Read
  - Bash
  - mcp__ai-scientist__analyze_codebase
---

# Codebase Scanner

Produce a structured snapshot of an existing codebase to ground later research phases.

## Inputs
- `<input name="codebase_path">` — absolute path

## Steps
1. **Preferred**: call `mcp__ai-scientist__analyze_codebase(codebase_path=...)` — returns structured JSON.
2. **Fallback** (if MCP unavailable): use Glob/Grep manually:
   - Glob entry points: `**/main.py`, `**/app.py`, `**/index.{js,ts}`, `**/__main__.py`, `Cargo.toml`, `package.json`, `pyproject.toml`
   - Glob test files: `**/test_*.py`, `**/*.test.{js,ts}`, `**/tests/**`
   - Grep `class ` / `def ` / `function ` / `export class ` to count classes/functions per module
   - Read manifest files (`package.json`, `pyproject.toml`, etc.) to extract dependencies
3. Compose result:

```json
{
  "language": "...",
  "framework": "...",
  "entry_points": ["..."],
  "modules": [{"name": "...", "files": N, "classes": N, "functions": N}],
  "dependencies": {"runtime": [...], "dev": [...]},
  "test_coverage_estimate": "...",
  "key_patterns": [...],
  "extension_points": [...]
}
```

## Output

Wrap the JSON in `<output name="codebase_analysis_json">...</output>`.
```

Commit: `feat(agents): codebase-scanner (sonnet 8k)`

### Task 16: `agents/literature-searcher.md`

```markdown
---
name: ai-scientist-literature-searcher
description: Runs the 8-query strategy across 6 academic sources (Semantic Scholar, OpenAlex, arXiv, bioRxiv, PubMed, Consensus, Anna's Archive) in parallel. Deduplicates, validates metadata via Crossref/OpenAlex, throttles per-source. Returns a unified paper list.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
tools:
  - WebFetch
  - mcp__arxiv__search_papers
  - mcp__biorxiv__search_preprints
  - mcp__pubmed__search_articles
  - mcp__annas-mcp__article_search
---

# Literature Searcher

Run the 8-query strategy from `search-queries.md` against all enabled sources, dedupe, validate metadata.

## Inputs
- `<input name="topic">`
- `<input name="domain">`
- `<input name="queries">` — list of 8 base queries from skill
- `<input name="prior_queries">` — list from trajectories.jsonl
- `<input name="source_toggles">` — which of 6 sources are enabled
- `<input name="rate_limit">` — OpenAlex req/s
- `<input name="metadata_validation_mode">` — "strict" | "off"

## Steps
1. **Per-source dispatch (parallel WebFetch + MCP calls):**
   - Semantic Scholar: WebFetch `https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=...&limit=20`. Header `x-api-key: ${env:SEMANTIC_SCHOLAR_KEY}` if set; else skip (search endpoint requires key).
   - OpenAlex: WebFetch `https://api.openalex.org/works?search=...&per-page=20&filter=from_publication_date:2024-01-01&select=...`. Append `&mailto=${env:OPENALEX_EMAIL}` if set. Throttle to `rate_limit` req/s.
   - arXiv: `mcp__arxiv__search_papers(query=...)`.
   - bioRxiv: `mcp__biorxiv__search_preprints(query=...)` (only if domain==computational_biology).
   - PubMed: `mcp__pubmed__search_articles(query=...)`.
   - Anna's Archive: `mcp__annas-mcp__article_search(query=...)`.
2. **Per-source response normalization** to unified schema:
   ```json
   {"title", "authors", "year", "doi", "journal", "url", "abstract", "source", "metadata_confidence"}
   ```
   For OpenAlex specifically, reconstruct abstract from inverted index (see search-queries.md).
3. **Merge + dedup**: by DOI (case-insensitive), then normalized title (lowercase, strip punct, first 80 chars). Prefer records with more complete metadata.
4. **Metadata cross-validation** (if `metadata_validation_mode == "strict"`):
   - For each paper with DOI: WebFetch `https://api.crossref.org/works/<doi>` and verify title+first-author+year. On mismatch, prefer Crossref record. Mark `metadata_confidence: "low"` and log discrepancy.
   - For papers without DOI: try OpenAlex resolve by title+author.
   - 3 validation failures → drop record, log to validation_log.
5. **Sort** by year descending, cap at `max_papers` (default 50).

## Output

```
<output name="paper_list_json">[...full list...]</output>
<output name="validation_log_json">[...corrections+drops...]</output>
```
```

Commit: `feat(agents): literature-searcher (sonnet 8k) with metadata validation`

### Task 17: `agents/hypothesizer.md`

```markdown
---
name: ai-scientist-hypothesizer
description: Produces a testable hypothesis with mathematical models, statistical framework, methodology, and codebase integration plan. Grounded in literature + prior meta-analysis.
model: opus
thinking:
  enabled: true
  budget_tokens: 64000
tools:
  - Read
  - Write
  - AskUserQuestion
  - mcp__ai-scientist__search_knowledge_index
  - mcp__ai-scientist__get_knowledge_details
---

# Hypothesizer

Generate `hypothesis.md` and `equations.txt` from literature + idea + prior knowledge.

## Inputs
- `<input name="topic">`, `<input name="domain">`
- `<input name="idea_json">` — from ideator
- `<input name="paper_list_compact">` — first 10 papers (title, first author, year, abstract snippet)
- `<input name="codebase_analysis">` — if present
- `<input name="prior_hypotheses">` — search results from `mcp__ai-scientist__search_knowledge_index(query=topic, mem_type="hypotheses")`
- `<input name="prior_failures">` — failure patterns from `get_meta_analysis()`

## Steps
1. **Recall**: use `mcp__ai-scientist__search_knowledge_index` for similar hypotheses.
2. **Generate** `hypothesis.md` with these sections:
   - Hypothesis (1 testable claim)
   - Mathematical Models (LaTeX in `\begin{equation}` / `\begin{align}`; every eq has verbal explanation)
   - Statistical Framework (H0/H1, test, alpha, multiple-comparison, effect size, CI, power)
   - Methodology (libs, exp type, metric, data sources, output artifacts; **explicit dependency list**)
   - Codebase Integration (if codebase present: new modules, extension points, API contracts)
   - Literature Grounding (cite by BibTeX key)
3. **Avoid prior failures**: if domain has high failure rate from `prior_failures`, simplify methodology.
4. **Extract equations** to `equations.txt` (content between `\begin{equation}`/`\begin{align}` blocks).
5. **[Checkpoint]**: if interactivity is "full", AskUserQuestion: "Hypothesis OK as drafted, or pivot toward [alternate angle]?"

## Output
```
<output name="hypothesis_md">...full markdown...</output>
<output name="equations_txt">...extracted equations...</output>
```
```

Commit: `feat(agents): hypothesizer (opus 64k)`

### Task 18: `agents/code-generator.md`

```markdown
---
name: ai-scientist-code-generator
description: Generates a runnable Python experiment script (experiment.py) plus its requirements.txt, implementing the methodology from hypothesis.md using only the domain template's preferred libraries.
model: opus
thinking:
  enabled: true
  budget_tokens: 48000
tools:
  - Read
  - Write
---

# Code Generator

Produce `experiment.py` + `requirements.txt`.

## Inputs
- `<input name="hypothesis_md">`
- `<input name="config_json">` — has preferred_libraries, experiment_type, evaluation_metric
- `<input name="codebase_analysis">` — if present, may extend existing modules

## Constraints
- Self-contained (no external data deps unless clearly available)
- `if __name__ == "__main__":` guard
- Saves `results.csv` (pandas DataFrame), `*.npy` raw data, plots in `figures/` (DPI 300, no top/right spines, no underscores in labels, large fonts, multi-panel via subplots)
- try/except around main computation; each plot in its own try/except
- Stdlib + pip-installable only (no system deps like CUDA libs)

## Output
```
<output name="experiment_py">...full Python source...</output>
<output name="requirements_txt">numpy>=1.26\npandas>=2.0\n...</output>
```

No markdown fences. No prose outside output tags.
```

Commit: `feat(agents): code-generator (opus 48k)`

### Task 19: `agents/experiment-runner.md`

```markdown
---
name: ai-scientist-experiment-runner
description: Installs requirements.txt into the per-job venv, runs experiment.py with timeout, parses stderr on failure, patches the script up to 3 rounds. Returns a structured run report.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
tools:
  - Bash
  - Read
  - Edit
  - Write
---

# Experiment Runner

Install deps, run, retry on failure with surgical patches.

## Inputs
- `<input name="output_dir">` — has `experiment.py`, `requirements.txt`, `.venv/`
- `<input name="auto_fix_max_rounds">` — default 3
- `<input name="timeout_seconds">` — default 300

## Steps
1. **Install**: `cd <output_dir> && .venv\Scripts\pip install -r requirements.txt` (Unix: `.venv/bin/pip`). Capture stderr.
2. **Run**: `cd <output_dir> && .venv\Scripts\python experiment.py > experiment_stdout.txt 2> experiment_stderr.txt` with timeout.
3. **Evaluate**:
   - exit 0 → done. Read results.csv, list .npy/figures/.
   - exit ≠ 0 → parse stderr, classify error (ImportError/SyntaxError/NameError/FileNotFoundError/Type/Value/Timeout). Apply minimal fix to `experiment.py` or `requirements.txt`. Re-run. Up to N rounds.
4. **Log fixes** to `experiment_fix_log.json`:
   ```json
   [{"attempt": 1, "error_type": "ImportError", "error_message": "...", "fix_applied": "...", "re_run_exit_code": 0}]
   ```
5. After exhaustion, return whatever state exists (do NOT silently proceed if final exit ≠ 0 — let orchestrator's Fixer flow take over).

## Output
```json
<output name="run_report">
{
  "final_exit_code": 0,
  "fix_attempts": 1,
  "stdout_summary": "...",
  "stderr_summary": "...",
  "results_csv_present": true,
  "npy_files": [...],
  "figures": [...],
  "fix_log": [...]
}
</output>
```
```

Commit: `feat(agents): experiment-runner (sonnet 8k)`

### Task 20: `agents/plotter.md`

```markdown
---
name: ai-scientist-plotter
description: Generates auto_plot_aggregator.py to produce 6-12 publication-quality figures from .npy files and results.csv. Reflects up to 3 rounds for completeness. Triggered standalone for "build plot for X" intents.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# Plotter

Aggregate experiment outputs into publication figures.

## Inputs
- `<input name="output_dir">` — has results.csv + .npy files
- `<input name="data_summary">` — column list, file shapes
- `<input name="reflection_max_rounds">` — default 3

## Steps
1. Read all .npy + results.csv from data_summary.
2. Generate `auto_plot_aggregator.py`:
   - Each plot in its own try/except
   - DPI 300, no top/right spines, no underscores in labels
   - Multi-panel via subplots (max 3 per row)
   - 6–12 figures total, all unique
3. Run aggregator: `cd <output_dir> && .venv\Scripts\python auto_plot_aggregator.py`. Capture stderr.
4. **Reflection** (up to N rounds): review figures dir. If <4 figures or missing axis labels/legends, revise script and rerun.
5. **[Checkpoint]** (interactivity="full"): AskUserQuestion presenting 4-6 figure thumbnails, ask which to keep/regenerate.

## Output
```
<output name="aggregator_py">...full script...</output>
<output name="run_report">{"figures_produced": N, "reflection_rounds": N, "final_status": "..."}</output>
```
```

Commit: `feat(agents): plotter (sonnet 8k)`

### Task 21: `agents/manuscript-writer.md`

```markdown
---
name: ai-scientist-manuscript-writer
description: Writes a complete LaTeX scientific manuscript by orchestrating 6 nested section subagents in parallel (Abstract, Introduction, Methods, Results, Discussion, Conclusion). Enforces consistency (citations, figure refs, no contradictions, no placeholders). Picks LaTeX template per settings.
model: opus
thinking:
  enabled: true
  budget_tokens: 48000
tools:
  - Read
  - Write
  - Task
---

# Manuscript Writer

Coordinate parallel section drafting and assemble manuscript.tex.

## Inputs
- `<input name="paper_list_compact">` — first 30 papers
- `<input name="references_bib_keys">` — list of BibTeX keys
- `<input name="hypothesis_summary">` — first 400 chars of hypothesis.md
- `<input name="experiment_summary">` — stdout first 500 chars + key metrics
- `<input name="codebase_analysis">` — if present
- `<input name="domain_extra_sections">` — from domain-templates.md
- `<input name="latex_template_path">` — chosen .tex template
- `<input name="tone">`, `<input name="citation_density">`

## Steps
1. **Build coordination plan**:
   ```json
   {
     "citation_budget": {"Introduction": 8, "Methods": 5, "Results": 3, "Discussion": 10},
     "shared_facts": [...],
     "figure_references": [...],
     "table_references": [...],
     "bibtex_keys_assigned": {"Introduction": [...], ...}
   }
   ```
2. **Dispatch 6 nested Task() calls in parallel** for: Abstract, Introduction, Methods, Results, Discussion, Conclusion. Each subagent receives the coordination plan + its assigned BibTeX keys. Each is dispatched with `subagent_type="ai-scientist-manuscript-writer"` recursively but with a `section: <name>` flag in the input — the prompt body handles this branch.
3. **Domain extras**: if `domain_extra_sections` non-empty, dispatch additional section subagents. Insert between Methods and Results.
4. **Assembly**: read template at `latex_template_path`. Stitch sections in order: preamble (template) → Abstract → Introduction → Methods → [extras] → Results → Discussion → Conclusion → references (\bibliography{references}).
5. **Consistency checks**:
   - Every `\cite{key}` exists in references.bib (input)
   - Every figure ref consistent across sections
   - No placeholder text (TODO, XXX, FIXME)
   - Abstract reflects Results

## Output
```
<output name="manuscript_tex">...full LaTeX...</output>
<output name="consistency_report">{"cite_warnings": [...], "figure_warnings": [...]}</output>
```
```

Commit: `feat(agents): manuscript-writer (opus 48k) with nested section subagents`

### Task 22: `agents/citator.md`

```markdown
---
name: ai-scientist-citator
description: Iteratively adds missing citations to references.bib (up to 5 rounds). Searches Semantic Scholar by topic gap. Never fabricates metadata.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
tools:
  - Read
  - Edit
  - Write
  - WebFetch
---

# Citator

Fill citation gaps in references.bib.

## Inputs
- `<input name="manuscript_tex">`
- `<input name="references_bib">`
- `<input name="max_rounds">` — default 5

## Steps
For each round (up to N):
1. Read current manuscript + bib.
2. Identify the most-needed missing citation (categories: methods comparison, background, tools, datasets).
3. WebFetch Semantic Scholar `https://api.semanticscholar.org/graph/v1/paper/search?query=<gap>&limit=5`.
4. If found with valid metadata, append BibTeX entry. Note where to cite.
5. If not found, skip and move on.
6. Stop early if no more gaps identified.

Rules: never fabricate. Skip duplicates (check existing keys). Clean BibTeX (escape `&`, `{`, `}`).

## Output
```
<output name="references_bib">...updated content...</output>
<output name="rounds_run">N</output>
<output name="citations_added">[{...}]</output>
```
```

Commit: `feat(agents): citator (sonnet 8k)`

### Task 23: `agents/reviewer.md`

```markdown
---
name: ai-scientist-reviewer
description: Performs NeurIPS-format peer review of the manuscript. Multimodal — also performs visual validation pass on rendered PDF/DOCX pages. Produces review.json + manuscript_v2.tex with top-3 fixes applied.
model: opus
thinking:
  enabled: true
  budget_tokens: 64000
tools:
  - Read
  - Write
  - AskUserQuestion
---

# Reviewer

Two modes: textual peer-review and visual-rendered-page validation.

## Inputs (textual mode)
- `<input name="manuscript_tex">`
- `<input name="references_bib">`

## Inputs (visual mode)
- `<input name="rendered_pages">` — list of PNG paths (from pdftoppm)
- `<input name="format">` — "latex" or "word"

## Textual review steps
1. Read manuscript end-to-end.
2. Score against rubric:
   - Originality, Quality, Clarity, Significance: 1–4
   - Soundness, Presentation, Contribution: 1–4
   - Overall: 1–10
   - Confidence: 1–5
3. Self-review checklist:
   - Every table number traces to experiment data
   - No placeholders (TODO/XXX/FIXME)
   - Abstract matches Results
   - All `\cite{}` exist in bib
   - All equations have verbal explanations
   - Figures referenced in text exist
   - No fabricated data
4. Generate Actionable_Fixes: top 3 specific, surgical fixes.
5. Apply top 3 fixes to manuscript → `manuscript_v2.tex`.

## Visual review steps
1. Read each PNG (multimodal).
2. Flag: overflowing tables, bad page breaks, missing figures, broken citations (`?` or `[?]`), unrendered math, ugly margins, font fallbacks.
3. Severity: high (blocks publication) | medium | low.
4. High-severity → orchestrator's Fixer flow.

## Output (textual)
```
<output name="review_json">
{
  "Summary": "...",
  "Strengths": [...],
  "Weaknesses": [...],
  "Originality": 3, "Quality": 3, "Clarity": 3, "Significance": 3,
  "Soundness": 3, "Presentation": 3, "Contribution": 3,
  "Overall": 6, "Confidence": 4, "Decision": "Accept",
  "Questions": [...], "Limitations": [...],
  "Actionable_Fixes": ["specific fix 1", "specific fix 2", "specific fix 3"]
}
</output>
<output name="manuscript_v2_tex">...with fixes applied...</output>
```

## Output (visual)
```
<output name="visual_review_json">
{
  "format": "latex",
  "pages_reviewed": N,
  "issues": [{"page": N, "severity": "high|medium|low", "description": "...", "suggested_fix": "..."}]
}
</output>
```
```

Commit: `feat(agents): reviewer (opus 64k) with multimodal visual validation`

### Task 24: `agents/meta-analyst.md`

```markdown
---
name: ai-scientist-meta-analyst
description: Reads all trajectories and jobs, computes per-domain success rates and failure patterns, writes meta_analysis.json + what_works.json with concrete recommendations for future jobs.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 8000
tools:
  - Read
  - Write
  - mcp__ai-scientist__run_meta_analysis
---

# Meta-Analyst

Cross-job learning extraction.

## Inputs
- `<input name="trajectories_jsonl">` — content of ~/.ai-scientist/trajectories.jsonl
- `<input name="jobs_json">` — content of ~/.ai-scientist/jobs.json

## Steps
1. **Preferred**: call `mcp__ai-scientist__run_meta_analysis()` — does the work + writes outputs.
2. **Fallback** (manual):
   - Compute success rate per domain
   - Compute avg manuscript words, papers found, fix attempts per domain
   - Identify common error types from fix logs
   - Extract reliable approaches (high success-rate patterns)
   - Build recommendations list

## Output
```
<output name="meta_analysis_json">{full structured analysis}</output>
<output name="what_works_json">{successful_patterns + recommendations_for_next_job}</output>
```
```

Commit: `feat(agents): meta-analyst (sonnet 8k)`

### Task 25: `agents/fixer.md`

```markdown
---
name: ai-scientist-fixer
description: Diagnoses pipeline failures (network, dependency, schema-mismatch, runtime, timeout, output-parse) and returns 2-4 concrete fix options for the orchestrator to surface to the user via AskUserQuestion. Never auto-applies fixes silently.
model: sonnet
thinking:
  enabled: true
  budget_tokens: 16000
tools:
  - Read
  - AskUserQuestion
---

# Fixer

Diagnose + propose. Never fix silently.

## Inputs
- `<input name="failed_phase">` — e.g. "literature", "experiment", "manuscript"
- `<input name="error_class">` — network|dependency|schema|runtime|timeout|output-parse
- `<input name="error_context">` — full stderr or malformed-output excerpt
- `<input name="current_state">` — list of artifacts on disk so far
- `<input name="prior_fix_attempts">` — list of fixes already tried this phase

## Failure-class playbook

| Class | Diagnose checklist | Typical fix options |
|---|---|---|
| network | Look for 429, DNS, timeout, SSL | (a) retry w/ backoff, (b) switch source, (c) set OPENALEX_EMAIL env, (d) skip source |
| dependency | ImportError, pip resolution conflict | (a) add to requirements.txt, (b) pin version, (c) substitute alternate package, (d) use system Python instead of venv |
| schema | Agent returned non-JSON or missing field | (a) re-prompt with schema reminder, (b) ask user for missing field, (c) relax constraint |
| runtime | TypeError/ValueError/FileNotFound in experiment.py | (a) patch line N, (b) wrap in try/except, (c) simplify computation, (d) switch to synthetic data |
| timeout | >300s | (a) reduce data, (b) simplify model, (c) raise timeout to N sec |
| output-parse | Manuscript missing section, malformed BibTeX | (a) regenerate failing section only, (b) ask user for tone preference, (c) escalate full state |

## Output

```
<output name="diagnosis">
{
  "root_cause": "...",
  "evidence": "...",
  "fix_options": [
    {"id": "a", "label": "Retry with exponential backoff", "details": "...", "estimated_success": 0.7},
    {"id": "b", "label": "Switch to OpenAlex (skip Semantic Scholar)", "details": "...", "estimated_success": 0.9},
    {"id": "c", "label": "Skip literature phase, proceed without papers", "details": "...", "estimated_success": 1.0, "side_effect": "manuscript will lack citations"}
  ],
  "recommended_option": "b"
}
</output>
```

The orchestrator surfaces these options to the user via AskUserQuestion. Never modify files directly.
```

Commit: `feat(agents): fixer (sonnet 16k) — diagnose-and-propose recovery`

---

## Task 26: Run static-checks test, expect all 12 to pass

- [ ] **Step 1: Run full static suite**

```bash
cd <PLUGIN_ROOT> && pytest tests/test_static_checks.py -v
```

Expected: all parametrized cases PASS. 0 failures.

- [ ] **Step 2: If any fail, fix the offending agent file (typo in frontmatter, missing key) and re-run.**

- [ ] **Step 3: Commit any frontmatter fixes**

```bash
git add agents/
git commit -m "fix(agents): frontmatter conformance fixes from static checks"
```

(Skip if step 2 was a no-op.)

---

# Phase E — Slash commands

## Task 27: Author 6 slash command files

**Files:**
- Create: `<PLUGIN_ROOT>\commands\ai-scientist.md`
- Create: `<PLUGIN_ROOT>\commands\ai-scientist-list.md`
- Create: `<PLUGIN_ROOT>\commands\ai-scientist-output.md`
- Create: `<PLUGIN_ROOT>\commands\ai-scientist-query.md`
- Create: `<PLUGIN_ROOT>\commands\ai-scientist-meta.md`
- Create: `<PLUGIN_ROOT>\commands\ai-scientist-resume.md`

Each file has the same shape: YAML frontmatter (`description`, `argument-hint`) + a body that reads "Invoke the ai-scientist skill with these args / context".

- [ ] **Step 1: Write `commands/ai-scientist.md`**

```markdown
---
description: Run the AI-Scientist research pipeline. Full or partial based on flags.
argument-hint: <topic> [--domain ml|optimization|statistical|mathematical|computational_biology|software_engineering] [--codebase <path>] [--output <dir>] [--full] [--only <agent>] [--no-word-export] [--reviewer-model opus|sonnet]
---

Invoke the ai-scientist skill with the user's full command line as the topic + flags. Skill handles argument parsing.

If `--full` is present, force the full 12-phase pipeline regardless of phrasing.
If `--only <agent>` is present, dispatch only that single agent.
Otherwise, the skill's Phase −1 classifier picks the agent subset.
```

- [ ] **Step 2: Write `commands/ai-scientist-list.md`**

```markdown
---
description: List all AI-Scientist research jobs.
---

Invoke the ai-scientist skill in "list jobs" mode. Read `~/.ai-scientist/jobs.json` and display a table: Job ID | Topic | Domain | Status | Date.
```

- [ ] **Step 3: Write `commands/ai-scientist-output.md`**

```markdown
---
description: Retrieve a section of a completed AI-Scientist job's output.
argument-hint: <job-id> [section: literature|hypothesis|manuscript|stats|all]
---

Invoke the ai-scientist skill in "get output" mode for the given job-id. Default section: all. Read from the job's output directory.
```

- [ ] **Step 4: Write `commands/ai-scientist-query.md`**

```markdown
---
description: Search the AI-Scientist persistent knowledge store (papers, hypotheses, benchmarks, claims).
argument-hint: <search terms>
---

Invoke the ai-scientist skill in "query knowledge" mode. Use SQLite FTS5 + ChromaDB hybrid search via `mcp__ai-scientist__search_knowledge_index`, then `get_knowledge_details` for top results. Also surface relevant `meta_analysis.json` insights and `what_works.json` recommendations.
```

- [ ] **Step 5: Write `commands/ai-scientist-meta.md`**

```markdown
---
description: View AI-Scientist cross-job meta-analysis.
---

Invoke the ai-scientist skill in "meta view" mode. Read `~/.ai-scientist/meta_analysis.json` and `~/.ai-scientist/what_works.json` and display: total jobs, success rate, avg manuscript length, per-domain stats, common failures, recommendations.
```

- [ ] **Step 6: Write `commands/ai-scientist-resume.md`**

```markdown
---
description: Resume a paused or failed AI-Scientist job from its last successful phase.
argument-hint: <job-id> [--from-phase <name>]
---

Invoke the ai-scientist skill in "resume" mode for the given job-id. The skill detects which artifacts exist on disk and resumes from the next phase. With --from-phase, force restart from that phase.
```

- [ ] **Step 7: Validate all 6 files parse**

```bash
python -c "
import re, yaml
from pathlib import Path
for f in Path(r'<PLUGIN_ROOT>\commands').glob('*.md'):
    text = f.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    assert m, f'{f.name}: no frontmatter'
    fm = yaml.safe_load(m.group(1))
    assert 'description' in fm, f'{f.name}: no description'
    print(f'{f.name}: OK')
"
```

Expected: 6 lines of `<file>: OK`.

- [ ] **Step 8: Commit**

```bash
git add commands/
git commit -m "feat(commands): 6 slash commands (ai-scientist + 5 subcommands)"
```

---

# Phase F — Settings

## Task 28: Author `settings/default-settings.json` and `settings/settings.schema.json`

**Files:**
- Create: `<PLUGIN_ROOT>\settings\default-settings.json`
- Create: `<PLUGIN_ROOT>\settings\settings.schema.json`

- [ ] **Step 1: Write default-settings.json**

Use the full settings tree from the design spec Section 11. Save it verbatim:

```json
{
  "plugins": {
    "ai-scientist": {
      "agents": {
        "ideator":             { "model": "opus",   "thinking_budget": 48000 },
        "codebase_scanner":    { "model": "sonnet", "thinking_budget": 8000 },
        "literature_searcher": { "model": "sonnet", "thinking_budget": 8000 },
        "hypothesizer":        { "model": "opus",   "thinking_budget": 64000 },
        "code_generator":      { "model": "opus",   "thinking_budget": 48000 },
        "experiment_runner":   { "model": "sonnet", "thinking_budget": 8000 },
        "plotter":             { "model": "sonnet", "thinking_budget": 8000 },
        "manuscript_writer":   { "model": "opus",   "thinking_budget": 48000 },
        "citator":             { "model": "sonnet", "thinking_budget": 8000 },
        "reviewer":            { "model": "opus",   "thinking_budget": 64000 },
        "meta_analyst":        { "model": "sonnet", "thinking_budget": 8000 },
        "fixer":               { "model": "sonnet", "thinking_budget": 16000 }
      },
      "interactivity": "checkpoints",
      "auto_fix_max_rounds": 3,
      "fixer_max_rounds_per_phase": 3,
      "phases": {
        "codebase_scan": "auto",
        "novelty_check": "on",
        "plot_aggregation": "on",
        "citation_enrichment": { "enabled": true, "max_rounds": 5 },
        "self_review": "on",
        "latex_compile": "auto",
        "word_export": "auto",
        "visual_validation": "on",
        "knowledge_index": "on",
        "meta_analysis": "on"
      },
      "manuscript": {
        "latex_template": "aiscientist-default",
        "word_template": "arxiv-shared-1",
        "tone": "technical",
        "citation_density": "medium"
      },
      "literature": {
        "max_papers": 50,
        "year_floor": 2024,
        "fallback_year_floor": 2020,
        "min_unique_threshold": 15,
        "metadata_validation": "strict",
        "openalex_rate_limit_per_second": 5,
        "sources": {
          "semantic_scholar": true,
          "openalex": true,
          "arxiv": true,
          "biorxiv": true,
          "pubmed": true,
          "consensus": true,
          "annas_archive": true
        }
      },
      "credentials": {
        "openalex_email": "${env:OPENALEX_EMAIL}",
        "semantic_scholar_key": "${env:SEMANTIC_SCHOLAR_KEY}"
      },
      "storage": {
        "knowledge_root": "~/.ai-scientist",
        "default_output_root": "./ai-scientist-output",
        "retain_completed_jobs_days": 90
      },
      "experiment": {
        "timeout_seconds": 300,
        "venv_per_job": true,
        "max_dependency_install_attempts": 2
      }
    }
  }
}
```

- [ ] **Step 2: Write settings.schema.json**

A JSON Schema (draft-07) covering the structure above. Key constraints:
- `agents.*.model` enum: ["opus", "sonnet", "haiku", "inherit"]
- `agents.*.thinking_budget` integer 0–128000
- `interactivity` enum: ["none", "checkpoints", "full"]
- `phases.*` enum: ["on", "off", "auto"] (or object form for citation_enrichment)
- `manuscript.latex_template` enum from template names
- `literature.metadata_validation` enum: ["strict", "off"]

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ai-scientist plugin settings",
  "type": "object",
  "properties": {
    "plugins": {
      "type": "object",
      "properties": {
        "ai-scientist": {
          "type": "object",
          "properties": {
            "agents": {
              "type": "object",
              "patternProperties": {
                "^[a-z_]+$": {
                  "type": "object",
                  "properties": {
                    "model": {"enum": ["opus", "sonnet", "haiku", "inherit"]},
                    "thinking_budget": {"type": "integer", "minimum": 0, "maximum": 128000}
                  },
                  "required": ["model", "thinking_budget"]
                }
              }
            },
            "interactivity": {"enum": ["none", "checkpoints", "full"]},
            "auto_fix_max_rounds": {"type": "integer", "minimum": 0, "maximum": 10},
            "fixer_max_rounds_per_phase": {"type": "integer", "minimum": 0, "maximum": 10},
            "phases": {
              "type": "object",
              "additionalProperties": {
                "oneOf": [
                  {"enum": ["on", "off", "auto"]},
                  {
                    "type": "object",
                    "properties": {
                      "enabled": {"type": "boolean"},
                      "max_rounds": {"type": "integer", "minimum": 0}
                    }
                  }
                ]
              }
            },
            "manuscript": {
              "type": "object",
              "properties": {
                "latex_template": {"enum": ["aiscientist-default", "overleaf-minimal", "elsevier-cas-sc", "ieee-conference", "acm-sig"]},
                "word_template": {"enum": ["arxiv-shared-1", "minimalist", "two-column-academic"]},
                "tone": {"enum": ["technical", "narrative", "balanced"]},
                "citation_density": {"enum": ["low", "medium", "high"]}
              }
            },
            "literature": {
              "type": "object",
              "properties": {
                "max_papers": {"type": "integer", "minimum": 5, "maximum": 200},
                "year_floor": {"type": "integer", "minimum": 1900, "maximum": 2100},
                "fallback_year_floor": {"type": "integer", "minimum": 1900, "maximum": 2100},
                "min_unique_threshold": {"type": "integer", "minimum": 1},
                "metadata_validation": {"enum": ["strict", "off"]},
                "openalex_rate_limit_per_second": {"type": "number", "minimum": 0.1, "maximum": 10},
                "sources": {
                  "type": "object",
                  "additionalProperties": {"type": "boolean"}
                }
              }
            },
            "credentials": {
              "type": "object",
              "properties": {
                "openalex_email": {"type": "string"},
                "semantic_scholar_key": {"type": "string"}
              }
            },
            "storage": {
              "type": "object",
              "properties": {
                "knowledge_root": {"type": "string"},
                "default_output_root": {"type": "string"},
                "retain_completed_jobs_days": {"type": "integer", "minimum": 1}
              }
            },
            "experiment": {
              "type": "object",
              "properties": {
                "timeout_seconds": {"type": "integer", "minimum": 30, "maximum": 3600},
                "venv_per_job": {"type": "boolean"},
                "max_dependency_install_attempts": {"type": "integer", "minimum": 1, "maximum": 5}
              }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 3: Validate defaults against schema**

```bash
pip install jsonschema
python -c "
import json, jsonschema
defaults = json.load(open(r'<PLUGIN_ROOT>\settings\default-settings.json'))
schema = json.load(open(r'<PLUGIN_ROOT>\settings\settings.schema.json'))
jsonschema.validate(defaults, schema)
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add settings/
git commit -m "feat(settings): default-settings.json + settings.schema.json"
```

---

# Phase G — Templates (LaTeX + Word)

## Task 29: Author 5 LaTeX templates

**Files:**
- Create: `<PLUGIN_ROOT>\mcp\templates\latex\aiscientist-default.tex`
- Create: `<PLUGIN_ROOT>\mcp\templates\latex\overleaf-minimal.tex`
- Create: `<PLUGIN_ROOT>\mcp\templates\latex\elsevier-cas-sc.tex`
- Create: `<PLUGIN_ROOT>\mcp\templates\latex\ieee-conference.tex`
- Create: `<PLUGIN_ROOT>\mcp\templates\latex\acm-sig.tex`

Each file is a LaTeX skeleton with placeholders the orchestrator fills.

- [ ] **Step 1: Write `aiscientist-default.tex`**

```latex
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{cite}
\usepackage{geometry}
\geometry{margin=1in}

\title{%TITLE%}
\author{%AUTHOR%}
\date{%DATE%}

\begin{document}
\maketitle

%ABSTRACT%

%INTRODUCTION%

%METHODS%

%EXTRA_SECTIONS%

%RESULTS%

%DISCUSSION%

%CONCLUSION%

\bibliographystyle{plain}
\bibliography{references}

\end{document}
```

- [ ] **Step 2: Write `overleaf-minimal.tex`**

```latex
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=2.5cm]{geometry}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{hyperref}

\title{%TITLE%}
\author{%AUTHOR%}
\date{%DATE%}

\begin{document}
\maketitle

%ABSTRACT%

%INTRODUCTION%

%METHODS%

%RESULTS%

%DISCUSSION%

%CONCLUSION%

\bibliographystyle{unsrt}
\bibliography{references}

\end{document}
```

- [ ] **Step 3: Write `elsevier-cas-sc.tex`**

```latex
\documentclass[a4paper,fleqn]{article}
% Approximation of Elsevier CAS single-column
\usepackage[utf8]{inputenc}
\usepackage[margin=2cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{natbib}
\usepackage{lineno}
\linenumbers

\title{%TITLE%}
\author{%AUTHOR%}
\date{%DATE%}

\begin{document}
\maketitle

\begin{abstract}
%ABSTRACT_BODY%
\end{abstract}

\textbf{Keywords:} %KEYWORDS%

%INTRODUCTION%
%METHODS%
%EXTRA_SECTIONS%
%RESULTS%
%DISCUSSION%
%CONCLUSION%

\bibliographystyle{elsarticle-num}
\bibliography{references}

\end{document}
```

- [ ] **Step 4: Write `ieee-conference.tex`**

```latex
\documentclass[conference,10pt]{IEEEtran}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{cite}

\title{%TITLE%}
\author{%AUTHOR%}

\begin{document}
\maketitle

\begin{abstract}
%ABSTRACT_BODY%
\end{abstract}

\begin{IEEEkeywords}
%KEYWORDS%
\end{IEEEkeywords}

%INTRODUCTION%
%METHODS%
%RESULTS%
%DISCUSSION%
%CONCLUSION%

\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
```

(Note: requires IEEEtran.cls — install script must check for it.)

- [ ] **Step 5: Write `acm-sig.tex`**

```latex
\documentclass[sigconf]{acmart}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}

\title{%TITLE%}
\author{%AUTHOR%}

\begin{document}
\begin{abstract}
%ABSTRACT_BODY%
\end{abstract}

\maketitle

%INTRODUCTION%
%METHODS%
%RESULTS%
%DISCUSSION%
%CONCLUSION%

\bibliographystyle{ACM-Reference-Format}
\bibliography{references}

\end{document}
```

(Note: requires acmart.cls — install script must check for it.)

- [ ] **Step 6: Smoke-compile each template (skipping placeholder substitution)**

For each template, replace the `%PLACEHOLDER%` tokens with stub text and run `pdflatex -interaction=nonstopmode <name>.tex`. Expect successful compile or graceful failure with a warning logged in the install script (some templates need extra .cls files).

- [ ] **Step 7: Commit**

```bash
git add mcp/templates/latex/
git commit -m "feat(templates): 5 LaTeX manuscript templates"
```

---

## Task 30: Source 3 Word templates with license verification

**Files:**
- Create: `<PLUGIN_ROOT>\mcp\templates\word\arxiv-shared-1.docx`
- Create: `<PLUGIN_ROOT>\mcp\templates\word\minimalist.docx`
- Create: `<PLUGIN_ROOT>\mcp\templates\word\two-column-academic.docx`
- Create: `<PLUGIN_ROOT>\mcp\templates\word\LICENSES.md`

- [ ] **Step 1: Search Anna's Archive / OpenAlex / GitHub for permissively-licensed Word templates**

Run a WebFetch sequence:

```
WebFetch https://github.com/search?q=arxiv+word+template+filetype:docx&type=code
WebFetch https://github.com/search?q=manuscript+template+filetype:docx+license:mit&type=code
```

Identify 3 candidates. Verify license via repository LICENSE file. Acceptable licenses: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, CC0, CC-BY-4.0.

- [ ] **Step 2: Download and place each .docx file**

Use `WebFetch` (URL→raw download) or `curl`. Place at the paths above.

- [ ] **Step 3: Write `LICENSES.md`**

```markdown
# Word Template Licenses

| Template | Source URL | Author | License | Notes |
|---|---|---|---|---|
| arxiv-shared-1.docx | <URL> | <author> | <SPDX-id> | <notes> |
| minimalist.docx | <URL> | <author> | <SPDX-id> | <notes> |
| two-column-academic.docx | <URL> | <author> | <SPDX-id> | <notes> |

All templates redistributed under their original licenses. Original license texts are preserved at the SOURCE_URL columns above.
```

Replace `<URL>`, `<author>`, `<SPDX-id>`, `<notes>` with the actual values from Step 1.

- [ ] **Step 4: Verify each .docx opens**

For each file, run a quick Python check:

```bash
pip install python-docx
python -c "
from docx import Document
for f in ['arxiv-shared-1.docx', 'minimalist.docx', 'two-column-academic.docx']:
    d = Document(rf'<PLUGIN_ROOT>\mcp\templates\word\{f}')
    print(f, ':', len(d.paragraphs), 'paragraphs')
"
```

Expected: 3 lines, each with paragraph count > 0.

- [ ] **Step 5: Commit**

```bash
git add mcp/templates/word/
git commit -m "feat(templates): 3 Word manuscript templates with license attribution"
```

**FALLBACK if no acceptable templates are found:** create blank `.docx` files using `python-docx` with author-provided default styles (Times New Roman 11pt, 1-inch margins, double-spaced). Add a note in LICENSES.md: "Templates auto-generated; restyle in Word as desired."

```python
from docx import Document
for name in ["arxiv-shared-1", "minimalist", "two-column-academic"]:
    d = Document()
    d.add_heading("%TITLE%", 0)
    d.add_paragraph("%AUTHOR%")
    d.add_paragraph("%DATE%")
    d.add_heading("Abstract", 1)
    d.add_paragraph("%ABSTRACT%")
    d.save(rf"<PLUGIN_ROOT>\mcp\templates\word\{name}.docx")
```

---

# Phase H — Scripts (PowerShell)

## Task 31: Write `scripts/install.ps1`

**Files:**
- Create: `<PLUGIN_ROOT>\scripts\install.ps1`

- [ ] **Step 1: Write file**

```powershell
# install.ps1 — one-time setup for ai-scientist plugin
$ErrorActionPreference = "Stop"
$PluginRoot = Split-Path -Parent $PSScriptRoot

Write-Host "AI-Scientist plugin install starting..." -ForegroundColor Cyan

# 1. Probe Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found in PATH. Install Python 3.11+ and re-run."
    exit 1
}
$pyver = & python --version 2>&1
Write-Host "  Python: $pyver"

# 2. Probe Pandoc
$pandoc = Get-Command pandoc -ErrorAction SilentlyContinue
if (-not $pandoc) {
    Write-Warning "  Pandoc not found. Word export will fall back to anthropic-skills:docx."
    Write-Warning "  Optional: winget install --id JohnMacFarlane.Pandoc"
} else {
    Write-Host "  Pandoc: $(& pandoc --version | Select-Object -First 1)"
}

# 3. Probe LibreOffice (for Word→PDF rendering for visual validation)
$libreoffice = Get-Command soffice -ErrorAction SilentlyContinue
if (-not $libreoffice) {
    Write-Warning "  LibreOffice not found. Visual validation of .docx will be skipped."
    Write-Warning "  Optional: winget install --id TheDocumentFoundation.LibreOffice"
} else {
    Write-Host "  LibreOffice: $($libreoffice.Source)"
}

# 4. Probe pdflatex
$pdflatex = Get-Command pdflatex -ErrorAction SilentlyContinue
if (-not $pdflatex) {
    Write-Warning "  pdflatex not found. LaTeX compile will be skipped (manuscript.tex still produced)."
    Write-Warning "  Install MiKTeX: winget install --id MiKTeX.MiKTeX"
} else {
    Write-Host "  pdflatex: $($pdflatex.Source)"
}

# 5. Probe pdftoppm (poppler) for visual validation
$pdftoppm = Get-Command pdftoppm -ErrorAction SilentlyContinue
if (-not $pdftoppm) {
    Write-Warning "  pdftoppm not found. PDF→PNG rendering for visual validation will be skipped."
    Write-Warning "  Install poppler: winget install --id oschwartz10612.Poppler"
}

# 6. Ensure ~/.ai-scientist/ exists
$aiHome = "$env:USERPROFILE\.ai-scientist"
if (-not (Test-Path $aiHome)) {
    New-Item -ItemType Directory -Path $aiHome | Out-Null
    Write-Host "  Created $aiHome"
} else {
    Write-Host "  Found existing $aiHome"
}

# 7. Pip-install MCP dependencies (user-site)
Write-Host "Installing MCP requirements..." -ForegroundColor Cyan
& python -m pip install --user -r "$PluginRoot\mcp\requirements.txt"

# 8. MCP self-test
Write-Host "Running MCP self-test..." -ForegroundColor Cyan
$selftest = & python "$PluginRoot\mcp\server.py" --selftest 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "MCP selftest failed:`n$selftest"
    exit 1
}
Write-Host "  $selftest"

# 9. Knowledge DB stats
$dbPath = "$aiHome\knowledge.db"
if (Test-Path $dbPath) {
    $size = (Get-Item $dbPath).Length / 1KB
    Write-Host "  knowledge.db: $size KB"
}

Write-Host ""
Write-Host "Install complete." -ForegroundColor Green
Write-Host "Next: run scripts\migrate-from-skill.ps1 to archive the old skill, then add the marketplace:"
Write-Host "  /plugin marketplace add `"C:\Users\danil\OneDrive\Рабочий стол\MCPs`""
Write-Host "  /plugin install ai-scientist@ai-scientist-local"
```

- [ ] **Step 2: Run install.ps1 (smoke test the script)**

```powershell
powershell -ExecutionPolicy Bypass -File "<PLUGIN_ROOT>\scripts\install.ps1"
```

Expected: green "Install complete." line, all probe results logged.

- [ ] **Step 3: Commit**

```bash
git add scripts/install.ps1
git commit -m "feat(scripts): install.ps1 with binary probing and selftest"
```

---

## Task 32: Write `scripts/migrate-from-skill.ps1` and `scripts/rollback.ps1`

**Files:**
- Create: `<PLUGIN_ROOT>\scripts\migrate-from-skill.ps1`
- Create: `<PLUGIN_ROOT>\scripts\rollback.ps1`

- [ ] **Step 1: Write `migrate-from-skill.ps1`**

```powershell
$ErrorActionPreference = "Stop"
$PluginRoot = Split-Path -Parent $PSScriptRoot
$OldSkill = "$env:USERPROFILE\.claude\skills\ai-scientist"
$BackupRoot = "$env:USERPROFILE\.claude\backups"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

if (-not (Test-Path $OldSkill)) {
    Write-Host "No legacy skill found at $OldSkill. Nothing to migrate." -ForegroundColor Yellow
    exit 0
}

# 1. Archive old skill
if (-not (Test-Path $BackupRoot)) {
    New-Item -ItemType Directory -Path $BackupRoot | Out-Null
}
$BackupDir = "$BackupRoot\ai-scientist-skill-$Timestamp"
Move-Item -Path $OldSkill -Destination $BackupDir
Write-Host "Archived $OldSkill -> $BackupDir" -ForegroundColor Green

# 2. Verify plugin assets
$RequiredFiles = @(
    "$PluginRoot\.claude-plugin\plugin.json",
    "$PluginRoot\skills\ai-scientist\SKILL.md",
    "$PluginRoot\mcp\server.py",
    "$PluginRoot\mcp\.mcp.json"
)
foreach ($f in $RequiredFiles) {
    if (-not (Test-Path $f)) {
        Write-Error "Missing required plugin file: $f"
        exit 1
    }
}
Write-Host "Plugin assets verified."

# 3. MCP selftest
$selftest = & python "$PluginRoot\mcp\server.py" --selftest 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "MCP selftest failed after migration:`n$selftest"
    Write-Error "Restoring backup..."
    Move-Item -Path $BackupDir -Destination $OldSkill
    exit 1
}

# 4. Knowledge DB sanity
$dbPath = "$env:USERPROFILE\.ai-scientist\knowledge.db"
if (Test-Path $dbPath) {
    $size = [math]::Round((Get-Item $dbPath).Length / 1KB, 1)
    $jobsPath = "$env:USERPROFILE\.ai-scientist\jobs.json"
    $jobCount = if (Test-Path $jobsPath) {
        (Get-Content $jobsPath | ConvertFrom-Json).PSObject.Properties.Count
    } else { 0 }
    Write-Host "  knowledge.db: $size KB, jobs registered: $jobCount" -ForegroundColor Green
}

Write-Host ""
Write-Host "Migration complete." -ForegroundColor Green
Write-Host "  Backup: $BackupDir"
Write-Host "  Test: /ai-scientist-list"
Write-Host "  Rollback: scripts\rollback.ps1 $Timestamp"
```

- [ ] **Step 2: Write `rollback.ps1`**

```powershell
param(
    [Parameter(Mandatory=$true)] [string]$Timestamp
)
$ErrorActionPreference = "Stop"
$BackupDir = "$env:USERPROFILE\.claude\backups\ai-scientist-skill-$Timestamp"
$Restore = "$env:USERPROFILE\.claude\skills\ai-scientist"

if (-not (Test-Path $BackupDir)) {
    Write-Error "No backup at $BackupDir"
    exit 1
}
if (Test-Path $Restore) {
    Write-Error "$Restore already exists. Move it aside first."
    exit 1
}
Move-Item -Path $BackupDir -Destination $Restore
Write-Host "Restored $BackupDir -> $Restore" -ForegroundColor Green
Write-Host "Note: plugin still installed. To uninstall, run: /plugin uninstall ai-scientist"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate-from-skill.ps1 scripts/rollback.ps1
git commit -m "feat(scripts): migrate-from-skill + rollback scripts"
```

---

## Task 33: Write `scripts/verify.ps1` (orchestrates static + MCP smoke + routing tests)

**Files:**
- Create: `<PLUGIN_ROOT>\scripts\verify.ps1`

- [ ] **Step 1: Write file**

```powershell
$ErrorActionPreference = "Stop"
$PluginRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== Static checks ===" -ForegroundColor Cyan
& python -m pytest "$PluginRoot\tests\test_static_checks.py" -v
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "=== MCP smoke test ===" -ForegroundColor Cyan
& python "$PluginRoot\mcp\server.py" --selftest
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "=== Routing tests ===" -ForegroundColor Cyan
& python -m pytest "$PluginRoot\tests\test_routing.py" -v
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "=== Settings schema validation ===" -ForegroundColor Cyan
& python -c "import json, jsonschema; jsonschema.validate(json.load(open(r'$PluginRoot\settings\default-settings.json')), json.load(open(r'$PluginRoot\settings\settings.schema.json')))"
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "  default-settings.json validates against schema. OK"

Write-Host ""
Write-Host "All checks passed." -ForegroundColor Green
```

- [ ] **Step 2: Commit**

```bash
git add scripts/verify.ps1
git commit -m "feat(scripts): verify.ps1 orchestrator for static+smoke+routing checks"
```

---

# Phase I — Routing tests

## Task 34: Author `tests/routing-fixtures.json`

**Files:**
- Create: `<PLUGIN_ROOT>\tests\routing-fixtures.json`

- [ ] **Step 1: Write fixtures**

```json
{
  "fixtures": [
    {"id": "review-1", "input": "review my paper at C:/papers/draft.tex", "expected_intent": "review-only", "expected_agents": ["ai-scientist-reviewer"]},
    {"id": "review-2", "input": "peer-review this manuscript", "expected_intent": "review-only", "expected_agents": ["ai-scientist-reviewer"]},
    {"id": "codebase-1", "input": "analyze the codebase at /Users/me/repo", "expected_intent": "analyze-codebase", "expected_agents": ["ai-scientist-codebase-scanner"]},
    {"id": "codebase-2", "input": "audit repo at C:/proj", "expected_intent": "analyze-codebase", "expected_agents": ["ai-scientist-codebase-scanner"]},
    {"id": "data-1", "input": "analyze results.csv from my experiment", "expected_intent": "analyze-data", "expected_agents": ["ai-scientist-plotter", "ai-scientist-meta-analyst"]},
    {"id": "plot-1", "input": "build plot for losses.npy", "expected_intent": "plot-only", "expected_agents": ["ai-scientist-plotter"]},
    {"id": "plot-2", "input": "make a figure visualizing accuracy over time", "expected_intent": "plot-only", "expected_agents": ["ai-scientist-plotter"]},
    {"id": "lit-1", "input": "find papers on protein folding", "expected_intent": "literature-only", "expected_agents": ["ai-scientist-literature-searcher"]},
    {"id": "lit-2", "input": "what's the state of the art in attention mechanisms?", "expected_intent": "literature-only", "expected_agents": ["ai-scientist-literature-searcher"]},
    {"id": "code-1", "input": "implement RWKV from scratch", "expected_intent": "code-only", "expected_agents": ["ai-scientist-code-generator"]},
    {"id": "code-2", "input": "write code for a benchmark and run it", "expected_intent": "code-only", "expected_agents": ["ai-scientist-code-generator", "ai-scientist-experiment-runner"]},
    {"id": "hypo-1", "input": "hypothesize what could explain the dropout effect", "expected_intent": "hypothesis-only", "expected_agents": ["ai-scientist-ideator", "ai-scientist-hypothesizer"]},
    {"id": "full-1", "input": "/ai-scientist linear regression on synthetic data --domain statistical", "expected_intent": "full-pipeline", "expected_agents": ["ai-scientist-ideator", "ai-scientist-codebase-scanner", "ai-scientist-literature-searcher", "ai-scientist-hypothesizer", "ai-scientist-code-generator", "ai-scientist-experiment-runner", "ai-scientist-plotter", "ai-scientist-manuscript-writer", "ai-scientist-citator", "ai-scientist-reviewer", "ai-scientist-meta-analyst"]},
    {"id": "full-2", "input": "research the impact of dropout on overfitting", "expected_intent": "full-pipeline", "expected_agents": ["ai-scientist-ideator", "ai-scientist-codebase-scanner", "ai-scientist-literature-searcher", "ai-scientist-hypothesizer", "ai-scientist-code-generator", "ai-scientist-experiment-runner", "ai-scientist-plotter", "ai-scientist-manuscript-writer", "ai-scientist-citator", "ai-scientist-reviewer", "ai-scientist-meta-analyst"]},
    {"id": "compound-1", "input": "look at the most advanced NN algorithms and write the code, then analyse", "expected_intent": "compound-lit-code-exp", "expected_agents": ["ai-scientist-literature-searcher", "ai-scientist-code-generator", "ai-scientist-experiment-runner", "ai-scientist-plotter"]},
    {"id": "compare-1", "input": "compare RWKV vs Mamba performance experimentally", "expected_intent": "comparison", "expected_agents": ["ai-scientist-code-generator", "ai-scientist-experiment-runner", "ai-scientist-plotter", "ai-scientist-meta-analyst"]},
    {"id": "msnft-1", "input": "write paper from C:/results/experiment-2026-04", "expected_intent": "manuscript-from-results", "expected_agents": ["ai-scientist-manuscript-writer", "ai-scientist-citator", "ai-scientist-reviewer"]},
    {"id": "ambig-1", "input": "do something with my data", "expected_intent": "ambiguous", "expected_agents": []}
  ]
}
```

- [ ] **Step 2: Validate JSON**

```bash
python -c "import json; data=json.load(open(r'<PLUGIN_ROOT>\tests\routing-fixtures.json')); print(len(data['fixtures']), 'fixtures')"
```

Expected: `18 fixtures`.

- [ ] **Step 3: Commit**

```bash
git add tests/routing-fixtures.json
git commit -m "test: 18 routing fixtures covering all 12 named intents"
```

---

## Task 35: Author `tests/test_routing.py`

**Files:**
- Create: `<PLUGIN_ROOT>\tests\test_routing.py`

This test does NOT actually invoke the LLM — it parses the routing-intents.md file + skill file and verifies that each fixture's expected_agents are mentioned in the intent's row in the routing table. This is a structural conformance check, not an LLM behavior test (those need an e2e harness).

- [ ] **Step 1: Write the test**

```python
"""Routing fixtures: each fixture's expected agents are listed in the corresponding intent row in routing-intents.md."""
import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ROUTING_DOC = PLUGIN_ROOT / "skills" / "ai-scientist" / "routing-intents.md"
FIXTURES = json.load(open(PLUGIN_ROOT / "tests" / "routing-fixtures.json"))["fixtures"]


def _parse_intent_table():
    """Return {intent_name: {agents: set}}."""
    text = ROUTING_DOC.read_text(encoding="utf-8")
    rows = {}
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] in ("#", "Name") or cells[0].startswith("---"):
            continue
        try:
            int(cells[0])  # number column
        except ValueError:
            continue
        name = cells[1]
        agents_text = cells[3]
        agents = set()
        for tok in re.split(r"[,/]| \(", agents_text):
            tok = tok.strip("() ")
            if tok and tok not in ("etc", "etc.", "—", "-", "none"):
                agents.add(f"ai-scientist-{tok.replace('_', '-')}")
        rows[name] = agents
    return rows


@pytest.fixture(scope="module")
def intent_table():
    return _parse_intent_table()


@pytest.mark.parametrize("fx", FIXTURES, ids=lambda f: f["id"])
def test_fixture_agents_subset_of_intent(fx, intent_table):
    intent = fx["expected_intent"]
    expected = set(fx["expected_agents"])
    if intent == "ambiguous":
        assert not expected, "ambiguous intent must have empty expected_agents"
        return
    assert intent in intent_table, f"intent {intent!r} not in routing-intents.md"
    declared = intent_table[intent]
    missing = expected - declared
    assert not missing, f"fixture {fx['id']!r} expects {missing} but routing doc declares {declared}"
```

- [ ] **Step 2: Run test**

```bash
cd <PLUGIN_ROOT> && pytest tests/test_routing.py -v
```

Expected: 18 PASSES (or 17 if ambiguous case is structured differently — adjust assertion).

If failures: the parsing in `_parse_intent_table` may need tuning to match the actual table format. Iterate until the parser correctly extracts agent sets.

- [ ] **Step 3: Commit**

```bash
git add tests/test_routing.py
git commit -m "test: routing-table conformance check against fixtures"
```

---

# Phase J — README and final integration

## Task 36: Write `README.md`

**Files:**
- Create: `<PLUGIN_ROOT>\README.md`

- [ ] **Step 1: Write README**

```markdown
# AI-Scientist Claude Code Plugin

End-to-end agentic research pipeline: literature search → hypothesis → experiment → manuscript → peer review. 12 dedicated subagents, each on a pinned model with extended thinking. Auto-routes natural-language requests ("review X", "plot Y", "code Z") to the smallest agent subset.

## Quick start (Windows)

```powershell
# 1. Install plugin dependencies
.\scripts\install.ps1

# 2. Migrate from old skill (one-time)
.\scripts\migrate-from-skill.ps1

# 3. Add the marketplace and install the plugin in Claude Code
# (run inside Claude Code)
/plugin marketplace add "C:\Users\danil\OneDrive\Рабочий стол\MCPs"
/plugin install ai-scientist@ai-scientist-local

# 4. Verify
.\scripts\verify.ps1
```

After install, the plugin appears in **Customize** with toggles for each agent's model and the per-phase enable flags.

## Usage

```
/ai-scientist <topic>                                       # full pipeline
/ai-scientist <topic> --domain ml --codebase C:/repo        # full pipeline with codebase grounding
/ai-scientist-list                                          # list jobs
/ai-scientist-output <job-id>                               # fetch artifacts
/ai-scientist-query <terms>                                 # search persistent knowledge store
/ai-scientist-meta                                          # meta-analysis view
/ai-scientist-resume <job-id>                               # resume failed job

review my paper at C:/papers/draft.tex                      # auto-routes to Reviewer only
build plot for losses.npy                                   # auto-routes to Plotter only
find papers on attention mechanisms                         # auto-routes to LiteratureSearcher only
look at advanced NN algorithms and write code, then analyze # multi-agent compound
```

## Tweaking

User overrides go in `~/.claude/settings.json`:

```json
{
  "plugins": {
    "ai-scientist": {
      "agents": {
        "reviewer": { "model": "sonnet", "thinking_budget": 32000 }
      },
      "interactivity": "full",
      "literature": { "max_papers": 30 }
    }
  }
}
```

See `settings/settings.schema.json` for the full schema.

## Architecture

- **12 subagents** (`agents/`): each pinned to opus or sonnet with its own thinking budget
- **Orchestrator skill** (`skills/ai-scientist/SKILL.md`): owns file I/O + Phase −1 intent routing + dispatch
- **MCP server** (`mcp/server.py`): job registry, knowledge store (SQLite + ChromaDB), meta-analysis
- **Templates**: 5 LaTeX, 3 Word; visual validation pass on rendered PNGs
- **Runtime data**: `~/.ai-scientist/` (knowledge.db, jobs.json, trajectories.jsonl) — preserved across plugin reinstalls

## Spec & plan

- Design: `docs/specs/2026-04-25-ai-scientist-plugin-design.md`
- Implementation plan: `docs/plans/2026-04-25-ai-scientist-plugin-implementation.md`

## License

MIT — see LICENSE.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quickstart, usage, and tweaking guide"
```

---

## Task 37: Install plugin in Claude Code and verify Customize visibility

**Files:** none (action task)

- [ ] **Step 1: In Claude Code, add the marketplace**

Run inside Claude Code:

```
/plugin marketplace add "C:\Users\danil\OneDrive\Рабочий стол\MCPs"
```

Expected output: `Added marketplace ai-scientist-local with 1 plugin.`

- [ ] **Step 2: Install the plugin**

```
/plugin install ai-scientist@ai-scientist-local
```

Expected: install confirmation; restart prompt if needed.

- [ ] **Step 3: Verify Customize visibility**

Open Claude Code's Customize / Plugins menu (depending on UI). The `ai-scientist` plugin entry must be visible with its description.

- [ ] **Step 4: Verify slash commands appear**

Type `/ai-scientist` in Claude Code. Expected: autocomplete shows the 6 slash commands.

- [ ] **Step 5: Verify MCP server connects**

Run:

```
/mcp
```

Expected: `ai-scientist` listed among connected MCP servers, status "ready".

- [ ] **Step 6: No commit (action task)** — record outcomes in a session note.

---

## Task 38: End-to-end smoke run

**Files:** none (validation task)

- [ ] **Step 1: Run synthetic-statistical pipeline**

In Claude Code:

```
/ai-scientist linear regression on synthetic data --domain statistical --interactivity none --no-word-export
```

- [ ] **Step 2: Wait for completion** (~3-5 minutes for the synthetic-statistical case)

- [ ] **Step 3: Verify outputs**

Check the output directory for:
- `config.json` ✓
- `idea.json` ✓
- `paper_list.json` (≥10 papers) ✓
- `references.bib` ✓
- `hypothesis.md` ✓
- `experiment.py` + `requirements.txt` ✓
- `experiment_stdout.txt` (no error) ✓
- `results.csv` ✓
- `figures/` (≥4 PNGs) ✓
- `manuscript.tex` ✓
- `review.json` (Overall ≥3) ✓

- [ ] **Step 4: Verify model assignment via telemetry**

Read recent telemetry to confirm:
- ideator dispatched at opus
- hypothesizer dispatched at opus with 64k thinking
- code-generator dispatched at opus
- experiment-runner dispatched at sonnet
- reviewer dispatched at opus with 64k thinking

(How telemetry is exposed depends on Claude Code version; alternative: add a `--trace` flag to skill that logs to `<output-dir>/dispatch_log.jsonl`.)

- [ ] **Step 5: Verify forced-failure recovery**

In a second test run, intentionally break by setting `experiment.timeout_seconds: 1` in settings. Run a fresh pipeline. Expected: experiment-runner times out → orchestrator dispatches Fixer → AskUserQuestion surfaces 3-4 options → on user pick (e.g. raise timeout to 300), recovery succeeds.

- [ ] **Step 6: Tag v1.0.0**

```bash
cd <PLUGIN_ROOT>
git tag -a v1.0.0 -m "ai-scientist plugin v1.0.0 — initial release"
```

- [ ] **Step 7: No commit (validation task)** — record results in a final report.

---

# Self-Review

**Spec coverage check** (each spec section → task that implements it):

| Spec section | Implemented in |
|---|---|
| §1 Goals | All tasks |
| §2 Non-goals | (explicit YAGNI; no tasks needed) |
| §3 Architecture (Approach B) | Task 12 (skill orchestrator) |
| §4 Plugin layout | Tasks 4, 14–25, 27, 29, 30 |
| §5 Agents (12 with pinned models + thinking) | Tasks 14–25 |
| §6 Orchestration flow | Task 12 |
| §7 Error handling (Fixer + user-in-the-loop) | Task 25 (fixer agent), Task 12 (Phase F in skill) |
| §8 Auto-routing from natural language | Tasks 11 (routing-intents.md), 12 (Phase −1 in skill), 34–35 (fixtures + tests) |
| §9 Literature search upgrades (metadata cross-validation, OpenAlex throttling) | Task 16 (literature-searcher), Task 28 (settings) |
| §10 Manuscript output (LaTeX + Word + visual validation) | Tasks 21 (manuscript-writer), 23 (reviewer multimodal), 29 (LaTeX templates), 30 (Word templates), 12 (Phase 8/8.25/8.5 in skill) |
| §11 Settings/tweaking surface | Task 28 |
| §12 MCP server wiring | Tasks 5, 6, 7 |
| §13 Migration plan | Task 32 |
| §14 Validation strategy | Tasks 13, 33–35, 38 |
| §15 Open questions deferred | (no implementation; tracked) |
| §16 Acceptance criteria | Task 38 verifies them |

All spec sections covered.

**Placeholder scan:**
- No "TBD", "TODO", "implement later", "fill in details" in tasks.
- Word templates (Task 30) have a defined fallback — not a placeholder.
- All test files have full code.
- All commit messages are concrete.

**Type/name consistency:**
- Agent name pattern `ai-scientist-<role>` used consistently in: `name:` frontmatter (Tasks 14–25), `subagent_type=` calls (Task 12), routing fixtures (Task 34), test parametrizations (Task 13).
- Settings keys use snake_case (`code_generator`); agent file names use kebab-case (`code-generator.md`); skill `subagent_type` uses kebab-case via `name:` (`ai-scientist-code-generator`). Tests verify this matches.
- Phase numbering preserves the original 5.5-before-5 quirk for faithful reproduction.

No issues found. Plan is ready for execution.

---

# Execution Handoff

Plan complete and saved to `docs\plans\2026-04-25-ai-scientist-plugin-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (recommended for this plan's size)** — Dispatch a fresh subagent per task using `superpowers:subagent-driven-development`. Two-stage review between tasks. Best fit because the plan has 38 tasks and many are independent (e.g., the 12 agent files can each be one subagent's work).

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batched with checkpoints for review.

Which approach?
