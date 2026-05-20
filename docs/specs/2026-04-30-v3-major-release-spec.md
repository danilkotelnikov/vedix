# v3.0 Major Release Spec — Vedix

**Date:** 2026-04-30
**Status:** proposal — single major release; no incremental v2.2; supersedes the v2.2 spec at `docs/specs/_superseded/2026-04-30-v2.2-capability-spec-SUPERSEDED.md`
**Trigger:** user direction — "I do not want v2.2 and v3. I want major v3. We cannot copy or take some others ideas like from Imbad0202/academic-research-skills, we must ideate something new."
**Naming:** v3.0 ships under a new commercial name (default recommendation: **Vedix**; see §2). The `ai-scientist-plugin` name is retired at v3.0 cut.
**Independence constraint:** zero copying from `Imbad0202/academic-research-skills`. Where they have solved a problem we also need to solve (integrity gates, claim audit, reviewer anti-anchoring, revision tracking, statistical fallacy detection, AI disclosure), we ship **our own clean-room designs** that are structurally and methodologically different. The novel approaches in §4 are the result.

**Companion documents (commercialization is tracked separately):**
- `docs/marketing/2026-05-20-vedix-marketing-brief.md` — **standalone marketing-analysis track**: idea, attitude, core problem, ICP, JTBD, positioning, channels, KPIs. Hand to a marketing analyst.
- `docs/specs/2026-04-30-v3-commercial-rebrand-and-monetization.md` — naming + payment-infrastructure rationale.

§8 of this spec stays focused on the engineering surface of the commercial layer (entitlement gating, job-queue infrastructure, tier limits as code). The *go-to-market* surface lives in the marketing brief.

---

## 1. Goals + non-goals

### 1.1 Goals

v3.0 is one cohesive product release that combines:

1. **Carry-over** of every v2.1.x capability that already works (Python orchestrator, 9 MCPs, cross-host parity, DOI-gated cross-validator, 3-cycle plotter, anti-LLMish Tier 1-4, Codex `spawn_agent` waves, MemPalace persistence).
2. **Six novel rigor tracks** (§4) — independently designed to solve research-pipeline rigor problems without borrowing taxonomy, pattern, or interface from any competitor.
3. **Six net-new capability tracks** (§5) — features neither we nor any competitor currently ship.
4. **Russian-language first-class output** + ГОСТ-7.0.5 + Cyrillic font stack (§6).
5. **Publisher template engine** with LaTeX ↔ Word parity for 6 major venues (§7).
6. **Commercial product layer**: rebrand, BYOK SaaS architecture, RU + global payment rails, marketing plan (§§ 2, 8, 9).

### 1.2 Non-goals (v3.0)

- Multilingual expansion beyond English + Russian (Spanish / German / French / Japanese / Chinese deferred to v3.1).
- Hosted compute (LLM inference on our servers). Stays BYOK.
- Web UI for the orchestrator (CLI + plugin host only; web UI deferred to v3.2).
- VS Code / JetBrains plugin distribution (CLI hosts only at v3.0).
- A trained linguistic classifier on languages other than English + Russian.

---

## 2. Naming + branding

### 2.1 Recommendation (default if you don't override)

**`Vedix`** (Latin script) / **`Ведикс`** (Cyrillic).

- Etymology: Slavic *vědĕti* "to know" + `-ix` software suffix.
- 5 letters, identical pronunciation in EN and RU (/ˈviː.dɪks/ and /ˈvʲe.dʲɪks/).
- Reads as a scholarly software tool, not as an AI product. The "AI" stays in the engine, never in the brand.
- Domain prospects: `vedix.ai`, `vedix.so` likely free; `vedix.com` requires whois confirmation.
- Trademark sweep: no major conflicts in software (class 9) or SaaS (class 42).
- Russian market resonance: the Slavic root makes it feel domestic without sounding parochial in English.

Backup options (only if Vedix fails the trademark sweep):

| Name | Notes |
|---|---|
| **Knowlex** / Нолекс | knowledge + lex; corporate-credible in EN; legal-tech vendor uses it in `.com` |
| **Verax** / Веракс | Latin "truthful"; positions us on rigor/fact-verification (matches our DOI-gate + claim-audit pipeline) |
| **Quaero** / Кверо | Latin "I seek" (etymology of *query*); the EU search project sunset its mark |

### 2.2 Pre-commit checklist (run before any code references the new name)

1. `whois vedix.ai`, `vedix.so`, `vedix.com`
2. USPTO TESS class 9 / class 42 live-marks search containing "Vedix"
3. Rospatent (fips.ru) Russian trademark search for active marks
4. `github.com/vedix` org availability
5. PyPI + npm: `vedix` package availability
6. crates.io + Docker Hub: same

If Vedix fails on any of (1)–(3), fall back to Knowlex; if Knowlex fails, fall back to Verax.

### 2.3 Surface rename (v3.0 cut)

| Surface | v2.1.x | v3.0 |
|---|---|---|
| Repo | `github.com/danilkotelnikov/ai-scientist-plugin` | `github.com/vedix/vedix` (org) |
| Package | `ai-scientist-plugin` | `vedix` (core) + `vedix-claude` / `vedix-codex` / `vedix-gemini` (host adapters) |
| MCP namespace | `mcp__ai-scientist__*` | `mcp__vedix__*` |
| Slash command | `/ai-scientist <topic>` | `/vedix <topic>` (also bound to `/research` as an alias) |
| Domain | none | `vedix.ai` + `vedix.ru` mirror |
| Docs site | repo README | `docs.vedix.ai` |
| Cache path | `~/.claude/plugins/cache/ai-scientist-plugin/...` | `~/.claude/plugins/cache/vedix/...` |
| Data dir | `~/.ai-scientist/` | `~/.vedix/` |

The old `ai-scientist-plugin` repo becomes a deprecation stub with a one-time migration helper that detects `~/.ai-scientist/` and `~/.claude/plugins/cache/ai-scientist-plugin/` and offers to migrate state to `~/.vedix/`. Stub maintained for 6 months.

---

## 3. Architecture overview

v3.0 keeps the v2.1.x foundation intact and layers new modules on top. Total module count rises from 17 to ~30. Cross-host parity (Claude Code + Codex CLI + Gemini CLI) preserved.

```
~/.vedix/
├── repo/                              # canonical clone (cloned by bootstrap)
│   └── plugins/vedix/
│       ├── .claude-plugin/plugin.json
│       ├── agents/                     # 20+ .md agent prompt templates
│       ├── mcp/
│       │   ├── server.py
│       │   ├── lib/
│       │   │   ├── orchestrator/       # 30 Python modules (was 17 in v2.1)
│       │   │   │   ├── # ── carry-over from v2.1 (17 modules) ─────────────
│       │   │   │   ├── status.py, decorators.py, tokens.py, extraction.py,
│       │   │   │   ├── convergence.py, schemas.py, fewshot.py, checkpoints.py,
│       │   │   │   ├── dispatch/{__init__.py,claude_code.py,codex_native.py,codex.py,gemini.py},
│       │   │   │   ├── reflection.py, ensemble.py, stage_gate.py, references.py,
│       │   │   │   ├── findings.py, mempalace_helpers.py, superpowers_bridge.py,
│       │   │   │   ├── pipeline.py, cross_validator.py, source_accounting.py,
│       │   │   │   ├── article_type.py, preflight.py, resource_ledger.py,
│       │   │   │   ├── plotter_loop.py, anti_llm_lint.py, reviewer_ledger.py,
│       │   │   │   ├── # ── new in v3.0 (13 modules) ──────────────────────
│       │   │   │   ├── failure_mode_learning.py     # §4.1 empirical failure taxonomy
│       │   │   │   ├── citation_graph.py            # §4.2 graph analytics over the references network
│       │   │   │   ├── counterfactual_probe.py      # §4.3 citation counterfactual auditing
│       │   │   │   ├── adversarial_review.py        # §4.4 same-reviewer dual-stance protocol
│       │   │   │   ├── semantic_revision_diff.py    # §4.5 embedding-level claim diff
│       │   │   │   ├── prereg_replay.py             # §4.6 pre-registration replay
│       │   │   │   ├── provenance_ledger.py         # §4.7 per-sentence provenance + auto-disclosure
│       │   │   │   ├── prefllight_dialog.py         # §5.1 form-driven research-setup
│       │   │   │   ├── numerical_audit.py           # §5.2 claim ↔ artifact numerical verification
│       │   │   │   ├── register_discriminator.py    # §5.3 retrieval + trained classifier hybrid
│       │   │   │   ├── rationale_writer.py          # §5.4 per-artifact explanatory rationale
│       │   │   │   ├── publisher_engine.py          # §7 LaTeX + Word parity engine
│       │   │   │   └── locale.py                    # §6 RU/EN routing + ГОСТ-7.0.5 citation backend
│       │   │   └── sakana/                          # vendored canonical Sakana (unchanged)
│       │   ├── requirements.txt
│       │   └── .mcp.json
│       ├── settings/
│       ├── scripts/
│       ├── skills/vedix/
│       └── templates/
│           ├── latex/                  # 23 venue templates, ALL bundled (§7)
│           ├── word/                   # 23 venue .dotx, ALL bundled (§7)
│           └── ai_disclosure/          # auto-disclosure templates per venue
├── palace/                            # MemPalace per-project memory
├── corpus/                            # curated per-discipline × per-language papers (§5.3)
│   ├── chemistry/        (150 OA papers × 7 languages, ChromaDB index)
│   ├── biology/          (150 × 7)
│   ├── medicine/         (150 × 7)
│   ├── physics/          (150 × 7)
│   ├── mathematics/      (150 × 7)
│   ├── geology/          (150 × 7)
│   ├── computer_science/ (150 × 7)
│   └── humanities/       (150 × 7)
├── classifiers/                       # trained models (§5.3) — per discipline × language
│   ├── register_{discipline}_{lang}.safetensors  # 8 disciplines × 7 languages = 56 models
│   └── manifest.json                  # model versions, training date, F1 on holdout
├── byok/                              # §3.2 BYOK provider config
│   ├── providers.json                 # active providers + fallback chain
│   └── secrets/                       # per-provider API keys (chmod 600)
└── knowledge.db                       # global cross-job knowledge store (carry-over)
```

### 3.2 BYOK provider abstraction (multi-vendor + Russia + China)

Vedix interfaces with LLM providers exclusively through a thin abstraction at `orchestrator/byok/`. The user configures one or more providers via `vedix provider add <name>`; the orchestrator routes each agent dispatch through the configured chain with automatic fallback.

**Supported providers at v3.0:**

| Family | Provider | SDK / endpoint | Region | Use-case |
|---|---|---|---|---|
| **Anthropic-direct** | Anthropic Claude | `anthropic` Python SDK | global | primary for Claude Code host |
| **OpenAI-direct** | OpenAI | `openai` Python SDK | global | primary for Codex host |
| **Google-direct** | Google Gemini | `google-generativeai` SDK | global | primary for Gemini host |
| **Routers** | OpenRouter | OpenAI-compatible REST | global | multi-model gateway; cheap unified billing |
| **Routers** | Together.ai | OpenAI-compatible REST | global | OSS-model gateway (Llama 3.x, Mixtral) |
| **Chinese-direct** | DeepSeek | OpenAI-compatible REST (`api.deepseek.com`) | CN/global | DeepSeek-V3 / R1 reasoning; very cheap |
| **Chinese-direct** | Qwen (Alibaba DashScope) | OpenAI-compatible REST + `dashscope` SDK | CN/global | Qwen 2.5 / 3 family |
| **Chinese-direct** | Moonshot (Kimi) | OpenAI-compatible REST (`api.moonshot.cn`) | CN | Kimi K2 |
| **Chinese-direct** | Zhipu GLM | OpenAI-compatible REST (`open.bigmodel.cn`) | CN | GLM-4 family |
| **Russian-direct** | Sber GigaChat | `gigachat` Python SDK (REST + OAuth2 with `mTLS`) | RU | RU-native; sanctions-safe; ГОСТ-aware prose |
| **Russian-direct** | YandexGPT | `yandex-cloud` Python SDK | RU | RU-native; Yandex Cloud auth |
| **Other** | Mistral AI | `mistralai` SDK | EU | EU-resident option |
| **Other** | Cohere | `cohere` SDK | global | RAG-tuned models |
| **Self-hosted** | Local OpenAI-compatible | any URL accepting OpenAI schema (vLLM, llama.cpp server, Ollama) | air-gapped | for sanctions-affected or privacy-strict users |

**Routing logic.** The user configures a **provider chain** like `gigachat → openrouter:anthropic/claude-opus-4 → openai:gpt-5-xhigh`. Each agent dispatch tries the first provider; on rate-limit / 5xx / context-overflow, it falls back to the next. The chain is per-agent-class configurable (e.g. for the `manuscript-writer` use Anthropic; for the `register-discriminator` use a cheaper Qwen).

**Key handling.** Keys live in `~/.vedix/byok/secrets/` with `chmod 600`. No key ever leaves the local machine. Vedix.ai SaaS never collects user LLM keys — even Pro users BYOK; what Pro pays for is *infrastructure* (MCPs, job queue, classifier hosting), not LLM tokens.

**Capability normalization.** The abstraction normalizes provider-specific quirks: GigaChat's mTLS auth, YandexGPT's IAM-token refresh, OpenRouter's `HTTP-Referer` header requirement, Moonshot's strict tool-calling schema. The `byok/capabilities.json` file declares per-provider feature support (tool-use? streaming? structured output? max context?). The dispatcher picks a provider that supports the features the agent needs.

**Cost ledger.** Every call is logged with `{provider, model, input_tokens, output_tokens, estimated_cost_usd}` in `~/.vedix/byok/cost_ledger.jsonl`. Aggregated by `vedix cost report --since 30d`.

---

## 4. Novel rigor tracks (clean-room independent designs)

These six tracks address problems competing projects also try to solve, but with **structurally and methodologically distinct** approaches. None of these are copied from `Imbad0202/academic-research-skills` or any other source; the designs are derived from first principles below.

### 4.1 Failure-Mode Learning

**Problem:** the pipeline can fail in many ways (hallucinated citations, broken code, shortcut reliance, fabricated methodology, etc.). A static checklist imported from a paper goes stale and may not match our actual failure distribution.

**Imbad's approach (what we are not doing):** import a taxonomy from a published study and check off named modes.

**Our approach:** **Empirical bottom-up taxonomy** derived from our own pipeline's failure history.

Mechanism:
1. Maintain a `~/.vedix/failure_corpus/` directory of historical pipeline runs that the user has marked as "failed in some way" (with `vedix mark-failure <job_id> --description '...'`).
2. A monthly batch (`scripts/learn_failure_modes.py`) clusters failure descriptions using sentence-transformers + HDBSCAN. Each cluster gets a synthetic name + a per-cluster detector function template.
3. The 5–15 most populated clusters become the **active failure-mode set** for the next release. Less-populated clusters live in a "watch list."
4. Each detector in the active set is a small Python function applied at the corresponding pipeline phase; if it fires, the run halts (block) or surfaces (warn) per cluster severity.
5. Failure modes are **versioned** (`failure_modes_v1.json`, `_v2.json`, …). The user sees the version on every run.

Why this is structurally different from any imported checklist:
- The taxonomy is **specific to this pipeline's actual failures**, not a generic research-process taxonomy.
- New failure modes can be added by users marking jobs as failed; the system learns.
- Detector functions are templates the system extends, not hand-curated rules.

Output artifact: `failure_modes.json` per run with the active version, which detectors ran, which fired.

### 4.2 Citation graph analytics

**Problem:** detecting when citations are decorative (don't actually support the surrounding claim), fabricated, or chronologically incoherent.

**Imbad's approach (what we are not doing):** classify each citation into 5 typed HIGH-WARN classes based on text-match heuristics.

**Our approach:** model the manuscript's reference network as a **directed multigraph** and compute graph-analytic signals.

Mechanism:
1. Build a graph G where nodes are paragraphs (~P) and references (~R). Each `\cite{key}` in paragraph p creates a directed edge `p → r`.
2. Compute per-paragraph signals:
   - **Citation density**: edges from this paragraph divided by paragraph word-count. Outliers (very high or very low) are suspicious.
   - **Citation freshness Gini**: distribution of cited-paper publication years; very high concentration in one year is suspicious (suggests cherry-picked corpus).
   - **Venue diversity**: number of unique journals/venues cited; low diversity suggests narrow source pool.
   - **Self-citation ratio**: fraction of citations sharing first-author with the manuscript's declared author list.
   - **Chronology violations**: cited paper's publication date is later than the manuscript draft date (impossible).
   - **Disconnected references**: BibTeX entries with no incoming `→` edge (dangling — never cited).
   - **Decorative citations**: citations within a paragraph whose removal does not change the LLM-judged "claim made by this paragraph." Computed by counterfactual perturbation (see §4.3).
3. Each signal becomes a row in `citation_graph_report.json` with a per-paragraph severity score.
4. The report is consumed by the manuscript-writer's reflection loop: paragraphs flagged for citation-density outliers or decorative citations get rewritten or have citations removed.

Why this is structurally different:
- Graph-theoretic signals (Gini, density, chronology) instead of text-matching classes.
- Computes properties of the **set** of citations, not per-citation labels.
- Decorative-citation detection is the only similar idea, but it is implemented via counterfactual perturbation (§4.3), not fuzzy matching.

Output artifact: `citation_graph_report.json`.

### 4.3 Counterfactual citation probing

**Problem:** detect when a citation is decorative — present for cosmetic credibility, not because it actually supports the claim.

**Imbad's approach (what we are not doing):** fuzzy-match the citation's abstract against the surrounding sentence; if no match, flag.

**Our approach:** **counterfactual perturbation** — replace each citation in turn with a confabulated-but-plausible alternative and ask an LLM-judge whether the surrounding claim still makes sense.

Mechanism:
1. For each `\cite{key}` in the manuscript, generate a "decoy" replacement citation: a confabulated bibliography entry with the same year and a thematically-adjacent title (generated by a small dedicated agent).
2. Render two manuscript variants:
   - **Variant A**: original manuscript.
   - **Variant B**: original manuscript with the citation replaced by the decoy.
3. Dispatch a small LLM-judge with the two variants and ask: "Are these making different claims?"
4. If the answer is "no" — the citation is decorative (the judge couldn't tell the difference, so the cited paper isn't actually doing work).
5. If the answer is "yes" — the citation is load-bearing.

Why this is structurally different:
- Probes whether the citation is **necessary**, not whether the cited content matches.
- Uses synthetic decoys, not external retrieval.
- Yields a binary load-bearing / decorative classification, with the reasoning auditable from the judge's response.

Performance: 1 LLM-judge call per citation. For a 180-citation manuscript: ~3-5 minutes wall-clock at standard rate limits. Caching keyed on (citation_key, paragraph_text) so re-runs are free.

Output artifact: `citation_loadbearing.json` per citation.

### 4.4 Adversarial multi-pass review

**Problem:** reviewers anchor on first impression; a single-pass review is a snapshot, not a robust judgment.

**Imbad's approach (what we are not doing):** blind pre-commitment in Phase 1 before reading the paper.

**Our approach:** **same-reviewer dual-stance protocol** — the same reviewer reviews the paper twice with explicit opposing stances; the verdict is the disagreement between the two.

Mechanism:
1. For each of the 3 biased reviewers (positive, negative, neutral), run two passes:
   - **Pass A**: "Steelman this paper. Find the strongest version of every argument. Argue for acceptance."
   - **Pass B**: given the Pass A review as input, "Break this. Find every weakness Pass A missed. Argue for rejection."
2. The reviewer's published score is the median of Pass A and Pass B Overall scores.
3. The reviewer's **disagreement signal** is the absolute difference. A reviewer with low disagreement is calibrated; with high disagreement is conflicted (the paper has both real strengths and real weaknesses).
4. Aggregate disagreement across the 3 reviewers (mean of three disagreement signals) becomes the **paper's robustness score** — papers with high robustness scores received judgments that survive adversarial probing.

Why this is structurally different from blind pre-commitment:
- No pre-commitment phase. Both passes see the paper.
- The signal is the **gap between two adversarial passes by the same model**, not "the model committed beforehand."
- Captures something different: how much the reviewer's verdict moves under adversarial pressure.

Output artifacts: `adversarial_review.json` (per-reviewer Pass A + Pass B + disagreement) and `paper_robustness.json` (aggregate).

### 4.5 Semantic revision diff

**Problem:** when a manuscript is revised, line-level diff shows what changed textually but not what changed *substantively*. Was a paragraph rewritten or merely rephrased?

**Imbad's approach (what we are not doing):** track which reviewer findings the author *claimed* to address vs. whether the diff actually changed.

**Our approach:** represent each claim as an embedding; compare claim embeddings between revisions.

Mechanism:
1. Extract the set of declarative claims from each revision of the manuscript (using a dedicated `claim_extractor` agent that returns a list of (paragraph_id, claim_text) tuples).
2. Embed each claim with the multilingual-e5 model.
3. Match claims across revisions by paragraph_id + nearest-neighbor in embedding space.
4. For each matched pair, compute cosine similarity:
   - sim > 0.95 → cosmetic rephrase (claim is the same)
   - 0.80–0.95 → minor refinement
   - 0.50–0.80 → substantive revision
   - < 0.50 → claim replaced or removed
5. New claims in the new revision that have no match in the old → additions.
6. Claims in the old revision with no match in the new → deletions.

Why this is structurally different from tracking author-claimed addressings:
- Operates on the actual semantic content, not on the author's narrative about the revision.
- Gives a continuous similarity score, not a yes/no "addressed."
- Surfaces deletions and additions that the author might not call out.

Output artifact: `semantic_revision_diff.json` per `--resume` run.

### 4.6 Pre-registration replay

**Problem:** post-hoc statistical fallacy detection (Simpson's paradox, p-hacking, multiple comparisons, etc.) is a checklist applied after the fact. The honest version is to commit to the statistical analysis plan before running the experiment.

**Imbad's approach (what we are not doing):** an 11-item fallacy checklist applied post-execution.

**Our approach:** **pre-registration replay** — the pipeline emits a pre-registration document before the experiment runs; results audit against the pre-registration; deviations are explicitly flagged as exploratory (not falsified).

Mechanism:
1. After Phase 2 (hypothesis) and before Phase 3 (codegen), the orchestrator emits `prereg.md` containing:
   - The exact hypothesis being tested
   - The primary outcome metric and its expected effect size
   - The statistical test that will be applied (with α, correction method, sample size)
   - The stopping criterion (when do we stop running?)
   - The success criterion (what counts as confirming the hypothesis?)
2. `prereg.md` is committed to the job's MemPalace with a sentinel.
3. After Phase 4 (experiment) and before Phase 5 (manuscript), the pre-reg-replay agent reads `prereg.md` AND `results.csv` AND `experiment_stdout.txt`. For each pre-registered test:
   - Verify the test was actually performed.
   - Verify the test used the pre-registered α and correction.
   - Verify the sample size matches.
   - Verify the stopping criterion was respected (no peeking, no early stop).
   - Verify the success criterion is interpreted as pre-registered.
4. Any test in the results not in the pre-registration → flagged as **exploratory** (an honest research outcome, not a falsification, but distinguishable from the confirmatory result).
5. The manuscript-writer is then constrained: confirmatory results go in the main Results section; exploratory results go in an "Exploratory analyses" subsection with the appropriate hedge ("This analysis was not pre-registered and should be interpreted as hypothesis-generating").

Why this is structurally different:
- Pre-commitment **before** the experiment, not a checklist **after**.
- Doesn't try to detect Simpson's paradox; it makes the analysis plan explicit so the user can see what was and wasn't pre-committed.
- The manuscript prose itself differentiates confirmatory from exploratory — the structural difference is visible in the output.

Output artifacts: `prereg.md`, `prereg_replay.json`, separate Results / Exploratory sections in `manuscript.tex`.

### 4.7 Provenance ledger + auto-disclosure

**Problem:** AI disclosure statements in journal submissions are usually boilerplate. They don't tell the reader which sentence was written by which model with what evidence. Reviewers and editors can't audit the work.

**Imbad's approach (what we are not doing):** venue-specific boilerplate generator.

**Our approach:** **per-sentence provenance ledger** — every sentence in the manuscript is tagged with which agent produced it, what evidence it relied on, how many reflection rounds it survived, which lint tier it passed. The disclosure section is auto-generated from the ledger.

Mechanism:
1. Every agent that contributes to the manuscript (ideator, hypothesizer, manuscript-writer, citator, plotter — for figure captions) writes per-sentence tags to a `provenance.jsonl` log:
   ```json
   {"sentence_id": "intro_3", "agent": "manuscript-writer", "model": "opus-4.7", "evidence": ["Smith2024", "Doe2023"], "reflection_rounds": 2, "lint_tier_passed": 3, "register_discriminator_score": 0.71, "ts": "2026-04-30T12:34:56Z"}
   ```
2. After Phase 5 (manuscript), the `provenance_ledger.py` module reads `provenance.jsonl` and produces:
   - `provenance.html` — color-coded manuscript with per-sentence provenance on hover (for the author's audit)
   - `ai_disclosure.md` — a venue-aware disclosure section with **actual** statistics: "Of N sentences, M (%) were generated by Anthropic Claude Opus 4.7 with median 2 reflection rounds; K (%) were generated by OpenAI GPT-5.5 with median 3 reflection rounds; J (%) were edited by the human author after initial generation."
   - `provenance_summary.json` — machine-readable stats for the venue's required JSON-LD disclosure
3. Per-venue disclosure templates (NeurIPS, ICML, ICLR, ACL, EMNLP, Nature, Science, ACS, Cell) live in `templates/ai_disclosure/{venue}.j2` and the auto-disclosure renders the appropriate template populated with the actual stats.

Why this is structurally different:
- Honest: the disclosure says what actually happened, sentence by sentence.
- Auditable: reviewer can hover any sentence and see provenance.
- Venue-aware boilerplate is just the rendering layer; the substance comes from the ledger.

Output artifacts: `provenance.jsonl`, `provenance.html`, `ai_disclosure.md`, `provenance_summary.json`.

---

## 5. Net-new functionality (independent of any competitor)

### 5.1 Form-driven pre-experimental dialog

New phase `-2` (runs before intent classification). An interactive structured form collects:

1. Research question (free-form)
2. Domain (8 niches; auto-pre-fills domain templates)
3. Article type (review / experimental / benchmark / theoretical / case-study / policy-brief)
4. Target venue (one of the registered venues)
5. Output language(s)
6. Compute budget (max external API requests; max wall-clock)
7. Codebase path (optional)
8. Existing literature corpus (optional — Zotero JSON / folder of PDFs / Obsidian)
9. Author list + ORCID + affiliations
10. Conflict-of-interest declarations
11. Funder acknowledgements

Output: `job_config.json`. Always-on by default; `--no-setup` opts out for scripted callers.

Implementation: cascading `AskUserQuestion` rounds (4 questions per round, 3 rounds = 12 questions).

### 5.2 Post-experiment numerical claim audit

After Phase 5 (manuscript drafting) and before Phase 6 (citations):

1. Parse the manuscript with a LaTeX-aware AST parser.
2. Extract every quantitative claim: numbers, percentages, accuracy / loss / F1 / AUC values, sample sizes.
3. For each claim, locate the source artifact:
   - Table values → `results.csv`
   - Figure caption claims → rendered PNG + figure data
   - Inline numbers → `experiment_stdout.txt`
4. Compute `claim_value` vs `artifact_value`. Tolerance: 1e-3 absolute / 1% relative.
5. Mismatches go into `numerical_audit.json` with `claim`, `claim_value`, `artifact_value`, `artifact_path`, `delta`, `severity`. Block-severity halts; warn surfaces in final summary.

### 5.3 Hybrid linguistic register discriminator (retrieval + trained classifier)

Two layers, both run at runtime in the manuscript-writer's reflection loop. Detailed dataset preparation and both training scripts (CPU + GPU paths) are spelled out below.

**Layer A — retrieval-grounded discriminator (always on; no training required).**

1. Per discipline (8 niches) × per language (7 languages — EN/RU/ES/DE/FR/ZH/JA per §6), curate ~150 OA papers into `~/.vedix/corpus/{discipline}/{lang}/`.
2. Embed paragraph chunks with `intfloat/multilingual-e5-large` into ChromaDB.
3. At runtime, for each manuscript paragraph: embed it, k-NN against the matching discipline+language corpus (k=5), score cosine similarity. If max similarity < 0.55, the paragraph reads out-of-register.
4. Dispatch a small LLM-judge with the paragraph + 3 retrieved corpus examples. Judge says: pass / fail-rewrite / fail-rewrite-with-suggestion.
5. Loop: max 2 retries per paragraph.

**Layer B — trained per-discipline × per-language classifier (always-on second pass).**

#### 5.3.1 Dataset preparation pipeline

A single end-to-end script `scripts/prepare_corpus.py` orchestrates the dataset build for all 8 × 7 = 56 (discipline, language) pairs. Idempotent: re-running skips already-completed steps.

Stages (each writes a checkpoint file under `~/.vedix/corpus/{discipline}/{lang}/.checkpoints/`):

| Stage | Input | Output | Tool / module |
|---|---|---|---|
| **1. Acquisition** | (discipline, lang, year_range) → 200 OA paper candidates | `acquisition.jsonl` (one paper per line: title, DOI, year, license, full-text URL, language) | `mcp__openalex`, `mcp__semanticscholar`, `mcp__arxiv`, `mcp__biorxiv`, `mcp__pubmed`, `mcp__annas-mcp__article_search` |
| **2. Download** | paper URLs (PDFs preferred; XML/HTML accepted) | `pdf/` directory (one PDF or XML per paper) | `mcp__annas-mcp__article_download`, `mcp__pubmed__get_full_text_article`, direct HTTPS via `httpx` |
| **3. Text extraction** | PDFs / XMLs | `text/{paper_id}.txt` with paragraph boundaries preserved | `pdfminer.six` for PDFs; `lxml` for JATS XML; `tika` fallback for layout-broken PDFs |
| **4. Language verification** | extracted text | filtered keep-list (papers whose detected language matches target) | `fasttext` lid.176.bin (loaded once into RAM) |
| **5. Segmentation** | per-paper full text | `paragraphs.jsonl` (one paragraph per line with `paper_id`, `section`, `text`, `n_words`) | `spacy` sentencizer + paragraph-boundary heuristic |
| **6. Deduplication** | paragraphs.jsonl | `paragraphs_dedup.jsonl` (cross-paper near-duplicates removed) | `datasketch` MinHashLSH at Jaccard 0.85 over 5-gram shingles |
| **7. Positive labeling** | paragraphs_dedup.jsonl | `positives.jsonl` with `label=1` (in-register, human-authored) | rule-based: section ∈ {Introduction, Methods, Results, Discussion, Conclusion} AND n_words ∈ [40, 400] |
| **8. Negative generation** | positives.jsonl | `negatives.jsonl` with `label=0` (AI-stylistic rewrite of positives) | dispatch `register-negative-generator` agent (uses configured BYOK provider) per paragraph, force Tier-1 AI-tells injection (excess vocabulary from Liang 2024, ICLR 2024 peer-review study) |
| **9. Train/val/test split** | combined positives + negatives | `train.jsonl` (80%), `val.jsonl` (10%), `test.jsonl` (10%) | stratified random split by paper_id (no paper leaks across splits) |
| **10. Statistics** | all the above | `corpus_stats.json` with class balance, n_samples, mean paragraph length, language confirmation rate | direct compute |

Total runtime for all 56 (discipline, language) pairs: ~12–24 hours one-time on a workstation with reasonable bandwidth. The `--only discipline=chemistry,lang=en` flag scopes to one pair (~30 minutes).

Storage footprint: ~3 GB per language across all 8 disciplines (PDFs + text + JSONL); 21 GB total for 7 languages.

License compliance: only papers with Creative Commons or other OA-permissive licenses are retained at stage 4. The license field is preserved end-to-end; the published corpus omits the PDF and ships only paragraph-level text + DOI for traceability.

#### 5.3.2 Training scripts (two paths: CPU and GPU)

Both scripts share the same data pipeline (read `train.jsonl` / `val.jsonl` / `test.jsonl`) and produce the same output layout. The choice of script depends on the available hardware. Hardware detection auto-routes if you run the parent dispatcher `scripts/train_register_classifier.py`.

##### 5.3.2.a CPU training — `scripts/train_register_classifier_cpu.py`

**Target hardware:** Intel Xeon 8368 (38 cores / 76 threads / 512 GB RAM), or any modern multi-socket Xeon / EPYC with ≥ 64 cores and ≥ 128 GB RAM. **No GPU required.**

**Model:** `microsoft/mDeBERTa-v3-small` (140M params, ~530 MB checkpoint). Multilingual, much smaller than XLM-R-large; fits comfortably in CPU RAM and trains in reasonable time on Xeon-class CPUs.

**Optimizer:** `torch.optim.AdamW` with mixed-precision bf16 (Xeon 8368 supports bf16 via AVX-512 BF16). Batch size 16 per gradient step; gradient accumulation × 4 → effective batch size 64. Learning rate 2e-5, linear warmup over 6% of steps, cosine decay.

**Command — what to launch:**

```bash
# Activate venv
source ~/.vedix/repo/venv/bin/activate   # Linux/macOS
# or: ~/.vedix/repo/venv/Scripts/Activate.ps1  # Windows

# Train ALL 56 (discipline, language) pairs sequentially, with checkpointing
python ~/.vedix/repo/plugins/vedix/scripts/train_register_classifier_cpu.py \
  --corpus-root ~/.vedix/corpus \
  --output-root ~/.vedix/classifiers \
  --languages en,ru,es,de,fr,zh,ja \
  --disciplines chemistry,biology,medicine,physics,mathematics,geology,computer_science,humanities \
  --model microsoft/mDeBERTa-v3-small \
  --batch-size 16 --grad-accum 4 \
  --lr 2e-5 --epochs 3 \
  --bf16 \
  --num-workers 12 \
  --resume-from-checkpoint auto \
  --log-to-tensorboard ~/.vedix/classifiers/tb_logs

# Train just one (discipline, language) pair
python .../train_register_classifier_cpu.py \
  --only-pair "chemistry:en"
```

**Runtime estimates (Xeon 8368, 76 threads, 512 GB RAM):**
- Per (discipline, language) pair: ~20–28 hours
- All 56 pairs sequentially: ~7–9 days continuous
- With `--parallel-pairs 4` (separate processes, each on 19 threads): ~2–3 days

**Output files (per pair):**

```
~/.vedix/classifiers/
├── register_chemistry_en/
│   ├── model.safetensors        # ~530 MB
│   ├── tokenizer.json
│   ├── config.json
│   ├── training_log.jsonl       # per-step loss + LR
│   ├── metrics.json             # final F1 / precision / recall on test split
│   └── checkpoint-best/         # best-val checkpoint for resume
├── register_chemistry_ru/...
├── ...
├── manifest.json                # all 56 models registered with version + F1
└── tb_logs/                     # TensorBoard event files
```

**Quality gate:** training auto-aborts a pair if validation F1 < 0.78 after 1 epoch (signals bad data); raises a warning and continues to the next pair. The pair must be debugged manually before re-running.

##### 5.3.2.b GPU training — `scripts/train_register_classifier_gpu.py`

**Target hardware:** NVIDIA RTX 4060 8 GB (or any GPU with ≥ 8 GB VRAM). Optimized for the 8 GB tier; will use more VRAM if available.

**Model:** `xlm-roberta-base` (278M params, ~1.1 GB checkpoint in fp16). Better quality than mDeBERTa-v3-small (expected +2–4 F1) but needs the GPU.

**Optimizer:** `torch.optim.AdamW`, fp16 mixed precision (RTX 4060 supports fp16 via Ampere/Ada Tensor Cores). Batch size 4, gradient accumulation × 16 → effective batch size 64. Same LR schedule as CPU.

**Memory plan (RTX 4060 8 GB):** Model (~1.1 GB fp16) + optimizer states (~2 GB Adam fp32 moments) + activations (~3 GB) + gradients (~1 GB) ≈ 7.1 GB peak. Fits with 1 GB headroom for cuDNN workspace. `gradient_checkpointing=True` is an escape hatch if OOM occurs on a sequence-length-512 batch.

**Command — what to launch:**

```bash
# Activate venv (same as above)
source ~/.vedix/repo/venv/bin/activate

# Train ALL 56 pairs sequentially
python ~/.vedix/repo/plugins/vedix/scripts/train_register_classifier_gpu.py \
  --corpus-root ~/.vedix/corpus \
  --output-root ~/.vedix/classifiers \
  --languages en,ru,es,de,fr,zh,ja \
  --disciplines chemistry,biology,medicine,physics,mathematics,geology,computer_science,humanities \
  --model xlm-roberta-base \
  --batch-size 4 --grad-accum 16 \
  --lr 2e-5 --epochs 3 \
  --fp16 \
  --gradient-checkpointing \
  --resume-from-checkpoint auto \
  --log-to-tensorboard ~/.vedix/classifiers/tb_logs

# Train just one pair
python .../train_register_classifier_gpu.py --only-pair "physics:ru"
```

**Runtime estimates (RTX 4060 8 GB):**
- Per (discipline, language) pair: ~6–10 hours
- All 56 pairs sequentially: ~2–3 weeks continuous
- Recommended: weekend run of 8–10 pairs at a time; pause + resume via `--resume-from-checkpoint auto`

**Output files:** identical layout to CPU path. The `manifest.json` records `device_trained_on: "cuda:0 NVIDIA RTX 4060"` per pair so users can verify provenance.

##### 5.3.2.c Auto-dispatcher — `scripts/train_register_classifier.py`

```bash
# Detects available hardware and picks CPU or GPU script automatically
python ~/.vedix/repo/plugins/vedix/scripts/train_register_classifier.py \
  --corpus-root ~/.vedix/corpus \
  --output-root ~/.vedix/classifiers \
  --auto
```

Detection logic:
1. If `torch.cuda.is_available()` AND `torch.cuda.get_device_properties(0).total_memory >= 7 * 1024**3`: dispatch GPU script.
2. Else if `psutil.cpu_count(logical=False) >= 16` AND `psutil.virtual_memory().total >= 64 * 1024**3`: dispatch CPU script.
3. Else: raise `HardwareInsufficientError` with explicit guidance to use a remote workstation or Pro-tier hosted training (Vedix.ai SaaS).

##### 5.3.2.d Distribution + inference

After training, the user has 56 model directories. They can:

- **Use locally** — runtime auto-loads the matching `~/.vedix/classifiers/register_{discipline}_{lang}/` per manuscript.
- **Publish** — `vedix model publish register_chemistry_en --to models.vedix.ai` uploads the model to the Vedix model registry. Reviewed by maintainers; if accepted, becomes the canonical model for that pair and ships in subsequent `vedix model fetch` updates.
- **Pull pre-trained** — `vedix model fetch` downloads the maintainer-curated canonical models from `models.vedix.ai`. Free for all tiers. Pro tier adds priority bandwidth + quarterly auto-update.

**Runtime inference cost.** With all 56 models loaded lazily, peak RAM during a manuscript run that touches 2 disciplines × 2 languages = 4 models ≈ 2 GB. Per-paragraph inference: ~30ms on CPU, ~5ms on GPU.

This is the **only** v3.0 component that requires training. Layer A works without any training and ships as the v3.0 baseline. Layer B is **always on by default** in v3.0 — every install gets pre-trained classifiers via `vedix model fetch` at install time (~6 GB download). Local re-training is opt-in for advanced users (`vedix model train`).

### 5.4 Per-artifact explanatory rationale files

For every major artifact (manuscript, plots, code, references, hypothesis, idea), the corresponding agent ALSO writes a `<artifact>.rationale.md` companion explaining:

- Why this artifact exists (which research question / hypothesis it serves)
- What decisions the agent made (competing options considered, choice rationale)
- What evidence the agent relied on (papers, numerical values, prior work)
- What the human researcher should verify (3-5 specific check-this items)
- What the agent is uncertain about (open questions, hedges)

Always-on by default; `--no-rationale` opts out.

Implementation: a new `rationale-writer` agent runs after each major phase, consumes the producing agent's decision log + key inputs, writes the markdown file.

### 5.5 Codebase-aware research mode

When `--codebase /path/to/repo` is supplied:

- Phase 0.75 codebase-scanner reads the entire repo, builds a graph of {files, functions, classes, imports}.
- The hypothesis-generator uses the codebase as the grounding source — every hypothesis must reference a specific module / function / data structure in the codebase.
- The experiment-runner can target a specific function as the system under test, not just running arbitrary code.
- The manuscript-writer cites the codebase as a "Software" reference per FORCE11 software citation principles.

### 5.6 Public-result reproducibility audit

For experimental papers, after Phase 8 (compile):

- The audit-agent runs the experiment one more time from clean state (fresh venv, no cached results) in a sandbox.
- Compares the fresh-run numerical results against the manuscript's claimed numbers.
- Flags any irreproducible result with `reproducibility_audit.json` + a `.rationale.md` documenting the divergence (was it stochastic? did the random seed not propagate? was there an off-by-one in the codepath that loaded results?).

### 5.7 Web UI for the orchestrator (absorbed from v3.1)

A browser app at `app.vedix.ai` (and a self-hostable container image `vedix/web:latest` for institutional / on-prem users) provides:

- **Job submission form** — same options as the CLI; user picks discipline / language / venue / BYOK provider chain and submits.
- **Live progress stream** — Server-Sent Events feed of the orchestrator's phase progression; per-agent status, intermediate artifacts as they land.
- **Manuscript preview** — split-pane LaTeX source ↔ rendered PDF; click any sentence to see its provenance ledger entry (§4.7) and rationale (§5.4).
- **MemPalace browser** — UI over the project's MemPalace memory (search drawers, traverse tunnels, view stats).
- **BYOK provider config** — secure UI to add/remove/reorder providers in the §3.2 chain.
- **Cost ledger view** — graph of monthly LLM spend per provider per agent class.

Stack: **React 19 + TypeScript** + **TanStack Query** for server state + **shadcn/ui** for components + **react-pdf** for the preview pane. Backend talks to the Vedix.ai SaaS API (or the local plugin's `mcp__vedix` HTTP transport for on-prem).

### 5.8 IDE plugin distribution (absorbed from v3.1)

Two thin clients that wrap the CLI for users who don't want to leave their IDE:

**VS Code extension (`vedix.vedix`)**:
- Command palette: `Vedix: New manuscript`, `Vedix: Switch venue`, `Vedix: Run reproducibility audit`
- Side-panel job-progress view
- Hover-on-citation: shows provenance + counterfactual-probe verdict
- Status bar: current cost-ledger month-to-date

**JetBrains plugin (`vedix-jetbrains.jar`)** for IntelliJ IDEA / PyCharm / CLion / WebStorm:
- Tool window with the same surface as the VS Code extension
- Action: `Vedix → New Manuscript` keyboard shortcut

Both ship as **OSS** on their respective marketplaces (Marketplace + JetBrains Plugin Repository). Both call into the user's local CLI (`vedix ...`) or, if configured, the Vedix.ai SaaS.

### 5.9 Pre-print server auto-submission (absorbed from v3.1)

After a manuscript completes Phase 8 + parity check + AI-disclosure generation:

- **arXiv submission** — via the arXiv API + the user's stored arXiv credentials (chmod 600 in `~/.vedix/byok/secrets/arxiv.token`). Auto-fills metadata; user reviews + confirms the submission in their browser.
- **bioRxiv submission** — via Cold Spring Harbor's bioRxiv submission API.
- **OSF (Open Science Framework)** — via OSF's REST API with a user-stored personal access token.
- **SSRN** — via SSRN's author dashboard URL with auto-fill query parameters (SSRN does not offer a public submission API; we use deep-linked form pre-fill).
- **Institutional repositories** — via OAI-PMH for any repository that accepts SWORD v2 deposits.

CLI: `vedix submit-preprint --to arxiv|biorxiv|osf|ssrn|<institutional>`. The orchestrator never submits silently — every submission is a separate user-confirmed action.

### 5.10 Federated MemPalace (absorbed from v3.1)

For multi-lab collaborations: a MemPalace instance can be marked `shared` and federated to other Vedix users with read-only or read-write access via OAuth2-authenticated WebSocket.

- **Access model:** per-drawer ACL (private / lab-shared / org-shared / public).
- **Sync:** CRDT-backed; offline edits reconcile via Yjs at next connection.
- **Conflict resolution:** automatic CRDT merge for non-conflicting edits; explicit human resolution UI for conflicting edits on the same drawer.

CLI: `vedix palace share <palace> --to <email|org-id> --access read-write`.

### 5.11 Real-time multi-author collaboration (absorbed from v3.1)

For multiple authors editing the same manuscript concurrently:

- Manuscript edits propagated via **Y.js** CRDT over WebSocket.
- Cursor + selection presence shown in the Web UI.
- Reviewer comments are first-class CRDT entities (not the manuscript text itself, so they cannot accidentally drop edits).
- The provenance ledger (§4.7) records per-edit author identity, so the auto-disclosure file correctly attributes contributions per author.

This is the natural pair to §5.10; both are CRDT-backed and share the Y.js + WebSocket infrastructure.

---

## 6. Languages (all first-class at v3.0)

v3.0 ships first-class support for **7 languages**, each with native register classifier, citation-style backend, LaTeX font stack, Word template, and discipline-specific prose lints.

| # | Language | Code | Citation backend | LaTeX font stack | Register lint notes |
|---|---|---|---|---|---|
| 1 | **English** | `en` | numeric-comp, Vancouver, APA-7 | Latin Modern, Computer Modern | Tier 1–4 anti-LLMish lint per Liang 2024 |
| 2 | **Russian** | `ru` | ГОСТ-7.0.5-2008 | T2A fontenc + Noto Serif / CMU Cyrillic | impersonal-passive; flag «Кроме того», «Более того», «Также», «Стоит отметить», «Важно подчеркнуть», «Следует отметить»; em-dash budget 4 / 1k words |
| 3 | **Spanish** | `es` | ISO-690-2 (the de-facto Spanish-academic style) | Latin Modern + `\usepackage[spanish]{babel}` | flag clausulas pesadas paragraph-initial; «Es importante destacar», «Cabe señalar» |
| 4 | **German** | `de` | DIN 1505-2 | Latin Modern + `\usepackage[ngerman]{babel}` | flag overuse of «Hierbei», «Hingegen», «Darüber hinaus»; nominalization rate cap |
| 5 | **French** | `fr` | NF Z44-005 | Latin Modern + `\usepackage[french]{babel}` | flag «Il est à noter que», «Il convient de souligner» paragraph starts |
| 6 | **Chinese (Simplified)** | `zh` | GB/T 7714-2015 (with `\usepackage{gbt7714}`) | Source Han Serif SC / Noto Serif CJK SC | character-mode register classifier; flag overuse of 综上所述, 总而言之, 不仅...而且 transitions |
| 7 | **Japanese** | `ja` | JIS X 0202 (with `\usepackage[japanese]{babel}` via XeLaTeX) | Source Han Serif Japan / Noto Serif CJK JP | mode 敬体 vs 常体 consistency check; flag overuse of 〜と考えられる, 〜と思われる |

**Implementation outline (applies to every language):**

- ChromaDB corpus stored per (`discipline`, `lang`) at `~/.vedix/corpus/{discipline}/{lang}/`. See §5.3.1 dataset prep.
- Per-language register classifier shipped per §5.3.2 (mDeBERTa-v3-small CPU path; XLM-RoBERTa-base GPU path); 8 × 7 = 56 classifiers total.
- LaTeX engine selection: `pdflatex` for languages 1–5; `xelatex` (which handles CJK fonts natively) for `zh` + `ja`. The `publisher_engine` picks the engine per `--lang` flag.
- BibTeX entries preserve original-language orthography (no transliteration). Mixed-language reference lists are supported (a paper can cite both Russian and English sources side-by-side under any chosen output-language ordering).
- Word output `.dotx` templates per (`venue` × `lang`) — 23 venues × 7 languages = 161 total `.dotx` templates. All bundled at install (see §7).

**Out-of-scope languages at v3.0:** Traditional Chinese (`zh-TW`), Korean, Arabic, Hindi, Portuguese, Italian. Added via `vedix add-language` plugin point post-v3.0 if user demand surfaces.

---

## 7. Publisher template engine

`publisher_engine.py` provides LaTeX + Word output parity across **23 venue families** at v3.0, plus a publisher-neutral Overleaf-default preprint template for arXiv / OSF / SSRN / institutional repository use.

**Bundling decision (v3.0):** **all 23 templates are bundled at install.** No fetch-on-first-use. Every install carries every template + every (`venue` × `lang`) `.dotx` permutation. Rationale: zero network dependency at use time; predictable storage cost (~80 MB total for all LaTeX class files + Word templates + 7-language `.dotx` permutations + ai_disclosure variants); offline submission flows work end-to-end.

The engine is organized by **publisher family** rather than per-journal because most modern publishers ship a single LaTeX class that covers hundreds of their journals (e.g. `elsarticle.cls` covers > 2,000 Elsevier titles). Per-journal variants are layered on top via small JSON profiles that override section ordering, word limits, and reference-style sub-keys.

### 7.1 v3.0 venue catalog (all bundled)

| # | Venue family | Publisher | LaTeX class | Citation style | Region | Coverage |
|---|---|---|---|---|---|---|
| 1 | **Overleaf preprint default** (`preprint`) | publisher-neutral | `article.cls` 11pt single-column + `biblatex` (numeric-comp) | numeric-comp (arXiv-friendly) | global | arXiv, bioRxiv, OSF, SSRN, institutional repositories |
| 2 | **Nature** (Nature, Nat Comms, Nat Methods, Nat Mach Intell) | Springer Nature flagship | `nature.cls` | Nature | global | Nature family |
| 3 | **Elsevier** | Elsevier | `elsarticle.cls` | Elsevier numeric (`model3-num-names.bst`) | global | ~2,500 Elsevier titles (NeuroImage, Lancet*, Trends in *, etc.) |
| 4 | **Springer Nature journals** | Springer Nature | `sn-jnl.cls` | Springer numeric | global | ~3,000 Springer Nature journals |
| 5 | **Taylor & Francis** | Taylor & Francis | `interact.cls` | T&F numeric or author-date | global | ~2,700 T&F journals |
| 6 | **Frontiers** | Frontiers Media | `frontiers.cls` | Frontiers Reference Style (Vancouver-like) | global; OA | Frontiers in * family |
| 7 | **Wiley** | Wiley | `WileyNJD-v2.cls` | Wiley numeric | global | Wiley journals |
| 8 | **SAGE** | SAGE Publications | `sagej.cls` | SAGE author-date or Vancouver | global; social-sci heavy | SAGE journals |
| 9 | **PLOS** | Public Library of Science | `plos2015.cls` | Vancouver | global; OA | PLOS One, Biology, Comp Biol, etc. |
| 10 | **Cell Press** | Cell Press (Elsevier brand) | `cell.cls` | Cell | global | Cell, Neuron, Cell Reports |
| 11 | **IEEE** | IEEE | `IEEEtran.cls` | IEEE | global; CS/EE | all IEEE titles + conferences |
| 12 | **ACM** | ACM | `acmart.cls` | ACM (numeric) | global; CS | TOCHI, CACM, SIGGRAPH, etc. |
| 13 | **ACS** | American Chemical Society | `achemso.cls` | ACS | global; chemistry | JACS, JOC, OL, etc. |
| 14 | **MDPI** | MDPI | `mdpi.cls` | MDPI numeric | global; OA | MDPI titles |
| 15 | **AIP / APS** | AIP + APS | `revtex4-2.cls` | RevTeX numeric | global; physics | Physical Review, JCP, AIP Advances |
| 16 | **RSC** | Royal Society of Chemistry | `rsc.cls` | RSC author-date | global; chemistry | Chem Sci, Chem Comm, etc. |
| 17 | **Cambridge University Press** | CUP | `cambridge7A.cls` | author-date or numeric (per-journal) | global | Nature CUP family |
| 18 | **Oxford University Press** | OUP | `OUPMaths.cls` and `oup-contemporary.cls` (math vs other) | OUP styles | global | OUP titles |
| 19 | **BMJ** | BMJ Publishing Group | `bmj.cls` | Vancouver | global; medicine | BMJ, BMJ Open, etc. |
| 20 | **JAMA** | American Medical Association | `jama-style.cls` (in-house under MIT) | AMA | global; medicine | JAMA Network |
| 21 | **ГОСТ-generic** (ВАК-perechen' Russian) | publisher-neutral, ГОСТ-compliant | `gost-article.cls` + T2A | ГОСТ-7.0.5-2008 | RU | most ВАК-perechen' journals |
| 22 | **DAN RAS** (Доклады Российской Академии Наук) | RAS | `dan-ras.cls` (in-house under MIT) | ГОСТ-7.0.5 + DAN-specific section conventions | RU | Doklady Mathematics, Doklady Physics, Doklady Biological Sciences, etc. |
| 23 | **Uspekhi family** (Успехи Химии / Физики / Математических наук) | RAS Steklov + Kapitza Inst. | `uspekhi.cls` (in-house under MIT) | ГОСТ-7.0.5 + Uspekhi-specific review-article conventions | RU | Russ. Chem. Rev. / Phys. Usp. / Russ. Math. Surv. |

For every venue, the engine emits both:
- **LaTeX** — `manuscript.tex` + bundled `.cls` + `references.bib` → PDF via the appropriate engine (`pdflatex` / `xelatex` per §6)
- **Word** — `manuscript.docx` from a `.dotx` template, generated via `pandoc` + a venue-specific filter (`templates/word/{venue}_{lang}.dotx`)

Where the publisher does not distribute an open class file (e.g. JAMA, DAN RAS, Uspekhi), we author an in-house class file under MIT license that mimics the documented submission formatting. The `templates/<venue>/PROVENANCE.md` records: upstream-class-file source URL + license (or "in-house, MIT" + reference to the publisher's documented author guidelines).

### 7.2 Bundle composition + storage budget

Total bundle payload at install:

| Layer | Size |
|---|---|
| 23 LaTeX class files + their auxiliary files | ~12 MB |
| 23 × 7 `.dotx` Word templates (one per `venue × lang` pair = 161 files) | ~55 MB |
| 23 `ai_disclosure_<venue>.tex` templates | ~1 MB |
| Per-journal JSON profiles (top 200 journals across the 23 families) | ~1 MB |
| 23 `PROVENANCE.md` files | < 1 MB |
| **Total bundle** | **~70 MB** |

Bundle ships in the plugin install payload; no network calls needed at use time. Quarterly re-validation against publisher sources is a *maintainer* responsibility (CI job `verify-templates`), not a user-runtime concern.

### 7.3 Overleaf preprint default — design rationale

The `preprint` template is the **publisher-agnostic single-column default** for use when the author has not yet picked a target venue, is preparing an arXiv / bioRxiv / OSF deposit, or is iterating before submission:

- **Class:** standard `article.cls` (LaTeX2e core; no proprietary class file).
- **Layout:** 11pt, single-column, A4 (with US-letter switch flag), 1-inch margins.
- **Fonts:** Latin Modern Roman (default) + `lmodern` package. Russian variant uses `Noto Serif` + `T2A` fontenc. CJK variants use `Source Han Serif` via XeLaTeX.
- **Bibliography:** `biblatex` with `numeric-comp` style (arXiv-friendly) + `biber` backend; switch to `authoryear` via `--bib-style authoryear`.
- **Section structure:** abstract, keywords, 1 Introduction, 2 Related work, 3 Methods, 4 Results, 5 Discussion, 6 Conclusion, References, Appendix (in that order; reorderable).
- **No publisher branding.** No logo, no journal name, no copyright footer.
- **Word equivalent.** The `preprint.dotx` mirrors the same layout for Word users; both should render to PDF with identical section ordering, equation count, figure count, and reference count.

This is the template Vedix uses **by default** when the user does not pass `--venue`. It's also the template recommended for first-draft iteration before the author commits to a target journal.

CLI examples:

```
/vedix new "Effect of solvent polarity on Diels-Alder kinetics"
# defaults to --venue preprint

/vedix switch venue elsevier
# re-typesets to elsarticle.cls (already bundled at install)

/vedix switch venue elsevier:cell-reports-medicine
# uses elsarticle.cls + the Cell Reports Medicine per-journal JSON profile
# (section ordering, word limits, reference style sub-key)

/vedix switch venue gost-generic --lang ru
# Russian, ГОСТ-7.0.5

/vedix switch venue revtex42 --lang en
# AIP/APS RevTeX 4.2 — physics
```

### 7.4 Parity check (LaTeX ↔ Word)

After generating both `manuscript.pdf` and `manuscript.docx`, the publisher engine emits `parity_report.json` comparing them along:

- Section order
- Section title text (exact match, normalized whitespace)
- Number of equations, figures, tables, supplementary items
- Reference count
- Total word count (±2 % tolerance)
- Citation-call-out count (in-text citations match reference list cardinality)

Any divergence beyond tolerance is flagged in the report. Common causes: a figure was inserted in the LaTeX source but not exported to Word; a Word AutoCorrect changed a section title; a footnote in one is an endnote in the other. The report links each divergence to the source location for one-keystroke navigation.

### 7.5 Template provenance (legal hygiene)

All bundled templates derive from **publicly available submission guidelines and publisher-distributed class files** (e.g. Elsevier publishes `elsarticle.cls` on CTAN under LPPL; Frontiers publishes `frontiers.cls` on their website; Springer Nature publishes `sn-jnl.cls`). We embed only the open-license / publisher-distributed files and the publicly documented section / formatting rules — no copyrighted journal content (no sample articles, no editorial templates marked confidential).

Where the publisher does not distribute an open class file (JAMA, DAN RAS, Uspekhi), the corresponding class is authored in-house under MIT license. We document this explicitly in the per-template `PROVENANCE.md`.

Per-template `templates/<venue>/PROVENANCE.md` records: upstream class-file source URL, license, assembly date, and last quarterly re-validation date. CI job `verify-templates` re-validates against the upstream source URLs every release cycle.

### 7.6 Extension point

`vedix add-venue` is a documented schema for third-party contributors (and us, post-v3.0) to add venues without touching core. Each new venue ships as a directory with:

```
templates/<new_venue>/
├── latex/<new_venue>.cls
├── word/<new_venue>_<lang>.dotx   (× 7 languages)
├── ai_disclosure.tex
├── citation_style.json
├── profile.json                   (section ordering, word limits, etc.)
└── PROVENANCE.md
```

The engine auto-discovers new directories under `templates/` at startup; no code change required to add a venue.

---

## 8. Commercial layer (BYOK SaaS)

### 8.1 Product surface (everyone gets the full pipeline)

The free-tier plugin AND the free-tier Vedix.ai SaaS cover **the entire research pipeline**. Paid tiers buy **throughput and infrastructure**, not features. Free is the same Vedix the paying user has; paid is the same Vedix at higher rate.

**Free tier (plugin + SaaS, identical functionality):**

- Python orchestrator + **all 9 MCPs** (`ai-scientist`, `mempalace`, `openalex`, `semanticscholar`, `arxiv`, `biorxiv`, `pubmed`, `annas-mcp`, `fetcher`) — every MCP from §3 ships as Free infrastructure on the SaaS, so users who don't run a local Python stack still get the full search + memory + corpus surface.
- Cross-host parity (Claude Code + Codex + Gemini CLI)
- Layer A retrieval-grounded register discriminator (all 7 languages × 8 disciplines corpora bundled)
- Layer B pre-trained register classifier (all 56 (`discipline`, `lang`) models — fetched once via `vedix model fetch` at install or first SaaS sign-in)
- All 7 novel rigor tracks (§4)
- All 6 net-new functionality tracks (§5)
- **All 23 publisher templates bundled at install** + all 7 languages
- All 7 languages first-class
- BYOK across all supported providers (§3.2) — Anthropic, OpenAI, Google, OpenRouter, GigaChat, YandexGPT, DeepSeek, Qwen, Moonshot, Zhipu, Mistral, Cohere, self-hosted OpenAI-compatible

**Paid tiers buy throughput, not features.**

| Resource | Free | Solo | Lab | Institution |
|---|---|---|---|---|
| Hosted jobs per month | 2 (trial) | 20 | 200 | unlimited |
| Concurrent jobs | 1 | 2 | 8 | per-contract |
| MCP rate limit (queries/min per user) | 30 | 120 | 600 | per-contract |
| Job time limit (wall clock) | 30 min | 90 min | 4 hours | per-contract |
| Audit-log retention | 7 days | 30 days | 90 days | 1 year + on-prem option |
| Team shared MemPalace | ✗ | ✗ | ✓ (5 seats) | ✓ (unlimited seats) |
| SSO + RBAC | ✗ | ✗ | ✗ | ✓ |
| SLA | best-effort | 99.0% | 99.5% | 99.9% + on-prem |
| Priority bandwidth on model registry | ✗ | ✓ | ✓ | ✓ |
| Quarterly template re-validation | ✓ (community) | ✓ (priority) | ✓ (priority) | ✓ (priority) |

### 8.2 Tier structure (price points)

| Tier | RUB/mo | USD/mo | Best for |
|---|---|---|---|
| **Free** | 0 ₽ | $0 | Indie researcher; BYOK; 2 trial hosted jobs/month then run locally |
| **Solo** | 1,290 ₽ | $14 | Single researcher who wants hosted-job convenience + 20 jobs/mo |
| **Lab** | 4,900 ₽ | $49 | 5-person lab with shared MemPalace + 200 jobs/mo |
| **Institution** | from 24,900 ₽ | from $249 | University department or company R&D — SSO, on-prem, SLA, custom MCP rate |

### 8.3 Payment infrastructure

| Channel | Russia-resident? | Used for |
|---|---|---|
| ЮKassa | ✓ | RUB cards (Mir + Visa/MC) — primary RU rail |
| CloudPayments | ✓ | RUB cards — backup rail |
| Stripe | ✗ (RU cards) | Global cards (USD/EUR) — primary non-RU rail |
| Boosty | ✓ | Recurring micro-subs from RU patrons |
| Crypto (USDT TRC-20) | ✓ | Last-resort for sanctions-affected users |

Legal entity: **ИП-USN-6%** registered through Tinkoff (one-day online registration). Suitable up to 60M ₽/year revenue. Above that, migrate to ООО.

### 8.4 Marketing — moved out of this spec

Go-to-market — positioning, attitude, ICP, JTBD, channels (Habr / vc.ru / HN / arXiv methods paper / university seminars), funnel hypothesis, KPI framework, pricing-test instrumentation — lives in **`docs/marketing/2026-05-20-vedix-marketing-brief.md`**.

This spec only covers the *engineering* surface of the commercial layer (entitlement gating, job-queue infrastructure, tier limits encoded in `entitlements.py`, payment-webhook handlers). The marketing brief is the source of truth for *how customers find Vedix*; this spec is the source of truth for *how the SaaS is built*.

---

## 9. Timeline + phasing

Single major release. No v3.1 — everything previously deferred is in v3.0. v2.1.2 is the last v2.x.

| Block | Weeks | Tracks |
|---|---|---|
| **B1. Bootstrapping + rebrand** | 1 | Repo rename (`vedix/vedix`), package rename, MCP namespace rename (`mcp__vedix__*`), data-dir rename (`~/.vedix/`), migration helper, deprecation stub |
| **B2. BYOK multi-provider** | 3 | §3.2 abstraction layer + 13 provider adapters (Anthropic, OpenAI, Google, OpenRouter, Together, DeepSeek, Qwen, Moonshot, Zhipu, GigaChat, YandexGPT, Mistral, Cohere, self-hosted) + fallback chain + cost ledger |
| **B3. Novel rigor tracks** | 5 | §4.1–4.7: failure-mode learning, citation graph analytics, counterfactual probe, adversarial review, semantic revision diff, prereg replay, provenance ledger + auto-disclosure |
| **B4. Net-new functionality** | 3 | §5.1 setup dialog, §5.2 numerical audit, §5.4 rationale files, §5.5 codebase-aware, §5.6 reproducibility audit |
| **B5. Hybrid register discriminator + dataset prep + training scripts** | 5 | §5.3 corpus curation (8 disciplines × 7 langs), Layer A retrieval, Layer B classifier, `prepare_corpus.py`, CPU + GPU training scripts, model registry distribution |
| **B6. Languages (7 first-class)** | 4 | §6 EN/RU/ES/DE/FR/ZH/JA: citation backends, LaTeX font stacks, register lints, BibTeX preservation |
| **B7. Publisher engine (23 venues, all bundled)** | 4 | §7 all 23 templates × 7 languages × Word parity, in-house classes for JAMA/DAN/Uspekhi, vedix-add-venue extension point |
| **B8. Vedix.ai SaaS (all MCPs free)** | 4 | §8 FastAPI + Postgres + Redis backend, entitlement layer, ЮKassa + Stripe webhooks, hosted MCP fleet, job queue, cost ledger |
| **B9. Web UI for orchestrator** | 3 | Browser-based job submission, live progress, manuscript preview, MemPalace browse |
| **B10. IDE plugin distribution** | 3 | VS Code extension + JetBrains plugin (IntelliJ/PyCharm/CLion family) that wrap the CLI |
| **B11. Federated MemPalace + real-time collab + preprint auto-submit** | 4 | Cross-org shared memory + CRDT-backed real-time collab + arXiv / bioRxiv / OSF auto-submit |
| **B12. Polish + launch** | 2 | docs.vedix.ai site, demo videos, smoke testing, Habr / vc.ru / HN posts (per marketing brief) |
| **Total (serial)** | **41 weeks** (~10 months) | full v3.0 release |

Parallelizable down to ~22 weeks with 2 implementers; ~16 weeks with 3 implementers.

Block dependencies:
- B1 → all others (bootstrap is the foundation)
- B2 unblocks B3, B5 (rigor tracks + classifier training need provider routing)
- B3 + B4 can parallelize after B1, B2
- B5 (training) requires B6 (corpus prep depends on the 7 languages)
- B7 requires B6 (Word templates are per-language)
- B8 requires B2 + B3 + B4 + B5 (SaaS hosts the full pipeline)
- B9 + B10 require B8 (UI + IDE plugins talk to the SaaS API)
- B11 requires B8
- B12 is last

---

## 10. Open questions for the user

To unblock v3.0:

| # | Question | Default if you don't choose |
|---|---|---|
| 1 | Confirm name: **Vedix** (recommended), Knowlex, Verax, Quaero, or other? | Vedix |
| 2 | Form-driven setup: always-on or `--setup` opt-in? | always-on |
| 3 | Rationale files: always-written or `--explain` opt-in? | always-written |
| 4 | Counterfactual citation probe: run on every citation (default) or only top-cited (≥3 reuses; cheaper)? | every citation (~3-5 min for 180 cites) |
| 5 | Adversarial review: 2 passes per reviewer (default) or 3 passes (steelman / break / re-steelman)? | 2 passes |
| 6 | Pre-registration: hard-gate the experiment (must commit to prereg before running) or advisory (warn if prereg missing)? | hard-gate |
| 7 | Solo tier price: 1,290 ₽ or lower (990 ₽)? | 1,290 ₽ |
| 8 | Slash command: `/vedix <topic>` only, or both `/vedix` + `/research` alias? | both |
| 9 | Default BYOK provider chain when user has no key set: Anthropic-only / Anthropic→OpenAI→Google / open-source-only (DeepSeek→Qwen)? | Anthropic→OpenAI→Google (graceful degradation to cheapest available) |
| 10 | Web UI shipping as part of v3.0 launch or 4 weeks after as v3.0.1? | with v3.0 launch (it's in scope per "everything in v3") |

All ten are defaults-locked. Pick the subset you want to override; the rest stay as recommended.

---

## 11. Out of scope (post-v3.0 only)

Everything previously deferred to v3.1 was absorbed into v3.0. The only items that remain explicitly out of scope:

- **Hosted LLM inference** — we stay BYOK. Vedix never sells LLM tokens; users always own their LLM-provider relationships. This is a positioning choice, not a feature gap.
- **Mobile app** — research workflow is laptop-class; mobile is a different product surface.
- **Traditional Chinese, Korean, Arabic, Hindi, Portuguese, Italian** — explicitly out of v3.0 language scope; can be added via `vedix add-language` plugin point post-launch.
- **AAAS / Science** publisher template — no publicly distributed class file from the publisher; would require reverse-engineering against the author-guidelines PDF. Out of v3.0 to preserve provenance hygiene.
- **Hosted code-execution sandbox for experiments** — experiments still run on the user's local machine. Hosted sandbox runs are a hypothetical future tier that requires hardened sandboxing infrastructure and isn't in v3.0.
- **Auto-billing of LLM token costs** — we don't markup or rebill LLM tokens. BYOK only.
