# Source-Grounded Claim Architecture (SGCA) — Design Spec

**Status:** Approved 2026-05-20. Awaiting implementation plan.
**Owner:** Vedix v3.0
**Supersedes:** parts of §4.2, §4.3, §4.4, §4.7 — those tracks remain as orthogonal post-hoc audits, but the write-time approach moves under SGCA.
**Parent spec:** `docs/specs/2026-04-30-v3-major-release-spec.md`

---

## Problem

The v3.0 pipeline retrieves papers and feeds summaries/abstracts to the LLM as in-context free text. The only safety nets are *post-hoc*:

- §4.2 citation graph analytics — statistical signals over the reference list (Gini, density)
- §4.3 counterfactual citation probing — swap citation, ask if the claim still makes sense
- §4.7 provenance ledger — per-sentence agent/model tags, but no link to source content

**None of those check the claim against the source's actual content.** The LLM can:

- **Falsify** — write "Smith 2024 showed X" when Smith 2024 says ~X
- **Confabulate** — invent a claim, then attach a real-but-irrelevant citation post-hoc
- **Misparaphrase** — shift emphasis, scope, or sign of effect from the original
- **Ideate** — invent unsupported claims and attach citations the agent never read

Verification by reading the actual source paper, mid-pipeline, against a structured representation of what the source actually says — is the gap. SGCA closes it by making the source corpus *structurally first-class*.

---

## 1. Approach summary

The system maintains a multi-typed Knowledge Graph (KG) for every paper that touches the pipeline. KG nodes are the **only knowledge surface the LLM sees at writing time**. Writing is *constrained pre-generation*: before the LLM writes a paragraph, the orchestrator retrieves the allowed-set of KG nodes that paragraph may reference; the LLM produces sentences tagged with `cite | synthesize | speculate` buckets + anchor node IDs; a verifier intercepts every sentence and runs an entailment check against the anchor's verbatim quote. Speculations are never silently accepted — either pre-authorized at setup time or gated by live `AskUserQuestion`. Peer-reviewers run their own independent literature-search → graph-builder pipelines, building reviewer-KGs from possibly different sources; reviewer-KGs merge into the project-tier KG after review concludes, with cross-track confirms/contests edges preserved.

Both raw papers and structured KG fragments are preserved per tier. The KG is fully reconstructible from raw via `vedix kg rebuild`.

The KG lives in 4 tiers (job / reviewer-job / project / niche-cluster), each mapped to a MemPalace wing.

---

## 2. Architecture overview

```
WRITER TRACK (default pipeline, now constrained)
  Literature-Search → GraphBuilder → Hypothesizer → Code → Experiment → Manuscript
                          │
                          ▼
                      kg_writer (job-tier)
                          │
                          ▼
                  +───────┴───────+
                  │               │
              kg_project        kg_niche  (read-only, cross-project)
              (cached cross-run) (clustered by discipline subspecialty)

PEER-REVIEWER TRACK (NEW — per-reviewer, independent)
  Literature-Search-R → GraphBuilder-R → PR-Hypothesizer
                                          │
                                          ▼
                                  kg_reviewer_<id> (job-tier-reviewer)
                                          │
                                          ▼  (after review concludes)
                                    merged into kg_project
```

**Writing-time contract** — manuscript-writer receives, per paragraph, an allowed-set of KG nodes from `paragraph_planner`. Writer emits sentences tagged:

```
{
  text: "Diels-Alder kinetics scale with HOMO-LUMO gap [grounded:smith2024.claim03]",
  bucket: "cite",
  anchors: ["smith2024.claim03"]
}
```

`claim_verifier` intercepts each sentence:

- `cite` → load anchor's `verbatim_quote` + `paraphrase` from KG; run entailment check; reject + retry on fail
- `synthesize` → verify evidence path (≥2 anchors) is non-trivial
- `speculate` → check pre-authorization OR raise live `AskUserQuestion`; never silently accepted

Verification runs at v3.0 dispatch granularity (per-agent-class routing); cheap providers handle entailment, expensive providers handle writing. Latency ~3-5 s per sentence.

**Dual-layer storage** — both raw (PDF + plaintext + JATS XML) and structured (KG fragment + lattice contributions) preserved per tier. Raw is the immutable audit-trail; structured is the projection used at write-time.

---

## 3. Data model

### 3.1 Multi-typed KG fragment (per paper)

Each paper produces `structured/<paper_id>.kg.yaml` with the following:

```yaml
paper_id: smith2024_diels_alder
doi: 10.1021/jacs.4c00001
title: "Solvent polarity modulates Diels-Alder kinetics"
year: 2024
authors:
  - {id: author:JSmith, name: "J. Smith", orcid: "0000-0001-..."}
venue: "JACS"
language: en
license: CC-BY
raw_pointer:
  pdf:  raw/smith2024_diels_alder.pdf
  text: raw/smith2024_diels_alder.txt
  byte_len: 482310

nodes:
  claims:
    - id: smith2024.claim01
      type: empirical                  # empirical | methodological | review | theoretical
      paraphrase: "HOMO-LUMO gap correlates with Diels-Alder rate constant (r=0.78, n=42)"
      verbatim_quote: "We observed a strong correlation (r = 0.78, n = 42) between the HOMO-LUMO gap of the diene-dienophile pair and the second-order rate constant of cycloaddition."
      quote_byte_range: [38421, 38612]      # offset in raw/*.txt
      page: 4
      section: Results
      confidence: 0.94
      hedge: false
      entities: [entity:HOMO_LUMO_gap, entity:rate_constant, entity:cycloaddition]
      methods:  [method:DFT_b3lyp, method:HPLC_kinetics]
      limitations: [limit:smith2024.limit01]
      provenance: {extractor_model: "claude-opus-4", extractor_ts: 1716240000}

  methods:
    - id: method:DFT_b3lyp
      type: computational
      paraphrase: "DFT calculations at the B3LYP/6-31G(d) level"
      verbatim_quote: "All DFT calculations were performed at the B3LYP/6-31G(d) level using Gaussian 16."
      quote_byte_range: [12440, 12515]
      page: 2
      section: Methods

  results:
    - id: result:smith2024.r01
      paraphrase: "Pearson r=0.78, n=42, p<0.001"
      backs_claim: smith2024.claim01

  limitations:
    - id: limit:smith2024.limit01
      paraphrase: "Restricted to electron-poor dienophiles; electron-rich systems untested"

  entities:
    - {id: entity:HOMO_LUMO_gap, canonical_term: "HOMO-LUMO gap", lattice_link: concept:frontier_orbital_energy}
    - {id: entity:rate_constant, canonical_term: "second-order rate constant", lattice_link: concept:kinetic_rate}

edges:
  - {from: smith2024.claim01, to: smith2024.claim02, kind: extends}
  - {from: smith2024.claim01, to: smith2024.limit01, kind: limited_by}
  - {from: smith2024.claim01, to: method:DFT_b3lyp,  kind: uses_method}
  - {from: paper:smith2024,    to: smith2024.claim01, kind: contains}
  - {from: smith2024.claim01, to: paper:jones2022,   kind: cites}
  - {from: smith2024.claim01, to: jones2022.claim04, kind: contradicts}
```

**Closed node types**: `claim`, `method`, `result`, `limitation`, `entity`, `paper`, `author`.

**Closed within-track edge kinds (8)**: `contains`, `cites`, `extends`, `contradicts`, `uses_method`, `limited_by`, `supports`, `derives_from`.

**Closed cross-track edge kinds (3)** — used ONLY between writer-KG and reviewer-KG nodes, never inside a single track: `confirms`, `contests`, `independently_supports`. Defined in §5.3.

### 3.2 Concept lattice (cross-paper, SKOS-like)

Separate from per-paper KGs. Lives at `structured/_lattice/lattice.yaml` per tier.

```yaml
concepts:
  - id: concept:frontier_orbital_energy
    canonical_label_en: "frontier orbital energy"
    canonical_label_ru: "энергия граничных орбиталей"
    alt_labels: ["HOMO-LUMO gap", "frontier MO energy", "FMO gap"]
    broader:  [concept:molecular_orbital_theory]
    narrower: [concept:HOMO_energy, concept:LUMO_energy]
    related:  [concept:electron_affinity, concept:ionization_potential]
    appears_in_papers: [smith2024_diels_alder, jones2022_endo_exo]
    appearance_count: 28
    drift_warning: false
```

Maintenance: each new paper's extraction proposes lattice additions; `lattice_merger` auto-merges at `merge_confidence > 0.9`, surfaces conflicts to user otherwise via batched `AskUserQuestion` at end of GraphBuilder phase.

**`merge_confidence` computation** (deterministic, no LLM-judge bias in the threshold):

```
merge_confidence = 0.6 * embedding_cosine(label_A, label_B)        // multilingual-e5-large
                 + 0.3 * embedding_cosine(usage_context_A, usage_context_B)  // mean of 3 sample sentences each
                 + 0.1 * llm_judge_synonymy_probability(label_A, label_B)
```

where `usage_context` is the mean embedding of up to 3 randomly-sampled sentences in which each label appears. The 60/30/10 weights are calibrated against the gold-set lattice (§8.2) and reviewed quarterly.

### 3.3 Sentence bucket schema

Emitted by manuscript-writer, consumed by `claim_verifier`:

```yaml
# cite
- sentence_id: para_intro.s07
  text: "Diels-Alder kinetics scale linearly with HOMO-LUMO gap across electron-poor dienophiles [smith2024]."
  bucket: cite
  anchors:
    - {node_id: smith2024.claim01, anchor_role: primary}
  verifier:
    status: pass | fail-entailment | fail-bucket | pending-user-approval
    entailment_score: 0.93
    rationale: "Sentence paraphrases smith2024.claim01 within scope; limit01 acknowledged."
    ran_at_ts: 1716240120

# synthesize
- bucket: synthesize
  anchors:
    - {node_id: smith2024.claim01, anchor_role: support}
    - {node_id: jones2022.claim04, anchor_role: support}
  evidence_path: "smith2024.claim01 + jones2022.claim04 → general statement (cross-paper)"
  verifier.synthesis_check: pass | trivial-restatement | unsupported

# speculate
- bucket: speculate
  hedge_language: "we hypothesize that"
  authorization:
    source: setup_form | user_live_approval
    authorized_at: 1716239000
    authorized_by: scienceboylovesyou@gmail.com
  rationale_required: true
```

### 3.4 Storage layout (MemPalace mapping)

Each tier = one MemPalace wing; each paper / concept / job-state = one drawer.

```
~/.vedix/palace/
├── vedix_kg__job__<job_id>/                  ← job-tier (writer) wing
│   ├── drawers/
│   │   ├── meta__job_state.json
│   │   ├── paper__<paper_id>.json
│   │   ├── lattice__local.json
│   │   ├── outline__manuscript.json
│   │   ├── sentence_ledger.jsonl
│   │   ├── allowed_sets/<paragraph_id>.json
│   │   └── speculations.json
│   └── tunnels/
│       ├── edges.kg.jsonl
│       └── edges.bidir.idx
├── vedix_kg__reviewer__<N>__<job_id>/        ← reviewer-tier wing (one per adversarial reviewer)
│   ├── drawers/
│   │   ├── meta__reviewer_state.json
│   │   ├── paper__<paper_id>.json
│   │   ├── lattice__reviewer_local.json
│   │   ├── claim_redrivations.json
│   │   └── review__<claim_id>.json
│   └── tunnels/edges.kg.jsonl
├── vedix_kg__project__<project_id>/          ← project-tier wing
│   ├── drawers/
│   │   ├── meta__project.json
│   │   ├── paper__<paper_id>.json            ← deduped across all runs + reviewers
│   │   ├── lattice__project.json
│   │   ├── kg_provenance.json
│   │   └── job_history.json
│   └── tunnels/edges.kg.jsonl
└── vedix_kg__niche__<discipline>__<sub_niche>/  ← niche-tier (read-only)
    └── drawers/
        ├── meta__niche.json
        ├── lattice__niche.json
        ├── top_claims.json
        └── concept_clusters.json
```

Raw papers live outside MemPalace (too large for SQLite blobs):

```
~/.vedix/jobs/<job_id>/raw/
~/.vedix/projects/<project_id>/raw_cache/
```

---

## 4. Pipeline integration

### 4.1 New modules

| Module | Path | Responsibility |
|---|---|---|
| `graph_builder.py` | `orchestrator/sgca/` | Orchestrates per-paper extraction; merges fragments into job-tier KG; updates lattice |
| `kg_store.py` | `orchestrator/sgca/` | MemPalace adapter — read/write drawers, tunnels, lattice; per-tier APIs (`job`, `reviewer`, `project`, `niche`) |
| `claim_verifier.py` | `orchestrator/sgca/` | Bucket classification + entailment + path-check + speculation gate per sentence |
| `paragraph_planner.py` | `orchestrator/sgca/` | Per-paragraph allowed-set computation from manuscript outline + KG retrieval |
| `lattice_merger.py` | `orchestrator/sgca/` | Incremental lattice maintenance, confidence-thresholded auto-merge |

### 4.2 New agent

| Agent | Template | Responsibility |
|---|---|---|
| `paper-extractor` | `agents/paper-extractor.md` | Reads one paper's raw text, emits the full KG fragment per §3.1. ~1 dispatch per paper. Output: structured YAML, validated against pydantic schema. |

### 4.3 Modified existing modules

| Module | Change |
|---|---|
| `pipeline.py` | Inserts `GraphBuilder` phase between `LiteratureSearch` and `Hypothesizer`. Routes `manuscript-writer` through `paragraph_planner` for allowed-set computation. Inserts `claim_verifier` between writer-sentence-emission and accumulation. |
| `references.py` | Bibtex generation now reads from KG. Every `\cite{key}` mechanically maps to a KG `paper` node — eliminates dangling-citation and hallucinated-citation classes outright. |
| `dispatch/__init__.py` | New agent-class routing: `paper-extractor` → cheap+structured (Qwen-Max / DeepSeek-V3) by default. `claim-verifier` → cheap+fast. Manuscript-writer stays on premium provider per chain config. |
| `reviewer_ledger.py` | Each peer-reviewer gets its own KG namespace (`vedix_kg__reviewer__<N>__<job_id>`); reviewer-KGs merge into project tier after review concludes. |

### 4.4 Per-phase sequence

```
PHASE 0: Preflight + Setup
  - User completes ExperimentSetup form (§5.1 of parent spec)
  - Pre-authorized speculation themes (if any) captured here
  - Niche determined from {discipline, topic} → kg_niche tier mounted read-only

PHASE 1: Literature-Search [L]
  - Existing: search via 9 MCPs, produce paper_list.json
  - NEW: each result tagged with niche_hint for downstream graph-merger

PHASE 1.5: GraphBuilder [G]   ← NEW
  - For each paper in paper_list.json (parallel, 8-wide):
      1. Download raw PDF/XML via MCP
      2. Extract text → raw/<paper_id>.txt
      3. Dispatch paper-extractor → KG fragment
      4. Validate fragment against pydantic schema
      5. Run lattice_merger to integrate concepts
      6. Persist via kg_store.write_paper(job_tier, fragment)
  - Compute cross-paper edges (contradicts, extends, supports) via second pass:
        - Pairwise-candidate selection by embedding cosine (top-k=20 nearest claims per claim)
        - Dispatch paper-extractor agent in "cross-paper" mode given the 2 candidate claims + their verbatim quotes
        - Agent returns {edge_kind: contradicts|extends|supports|none, confidence}
        - Edges with confidence > 0.7 written to tunnels/edges.kg.jsonl
  - Lattice conflicts surface to user via batched AskUserQuestion
  - Emit kg_summary.yaml

PHASE 2: Hypothesizer [H]
  - Reads KG (job + project + niche tiers); never raw papers
  - Outputs hypothesis grounded in specific Claim nodes (anchors)

PHASE 3-5: Code → Experiment → unchanged

PHASE 6: Manuscript-Writer [M]
  - For each paragraph in outline:
      1. paragraph_planner.compute_allowed_set(paragraph_topic, hypothesis_anchors, kg)
         → ≤30 candidate nodes (claims, methods, entities, concepts)
      2. Writer agent dispatched with allowed_set as ONLY knowledge surface
      3. Writer emits sentences with {bucket, anchors}
      4. claim_verifier intercepts each sentence:
          - cite → entailment vs anchor's verbatim_quote
          - synthesize → verify path is non-trivial
          - speculate → check setup-form pre-auth OR AskUserQuestion gate
      5. Rejected sentences trigger rewrite (max 3 attempts), then bucket-switch, then hard-block

PHASE 7: Adversarial Peer-Review (extends §4.4)   ← NEW
  - For each adversarial reviewer N (1..3):
      1. Independent Literature-Search-R with stronger queries derived from manuscript abstract
      2. Independent GraphBuilder-R → reviewer-KG
      3. PR-Hypothesizer-R: re-derive claims from reviewer-KG, compare to writer's
      4. Emit review_R<i>.json with confirmed[], contested[], unsupported_by_R[]
      5. Reviewer-KG merges into kg_project (raw deduped against existing raw_cache)
```

### 4.5 Performance envelope

| Phase | First run | Cached run |
|---|---|---|
| GraphBuilder | 10–20 min (150 papers @ 8-wide parallel) | 2–5 min |
| Verifier overhead per sentence | ~3–5 s (cheap provider) | ~3–5 s |
| Verifier total per manuscript (~800 sentences) | ~40 min (concurrent with writing) | same |
| Adversarial peer-review (3 reviewers parallel) | 25 min | 15 min |
| **Total addition to pipeline** | **+60–80 min** | **+15–30 min** |

---

## 5. Adversarial peer-reviewer KG track

### 5.1 Per-reviewer pipeline

Each adversarial reviewer (N = 2 or 3 per parent-spec Q5) runs its own full L → G → H' track, in parallel, after the writer's manuscript draft is complete:

```
Reviewer-R_i (i in 1..N):
  Input: writer's manuscript abstract + headline claims (top-10 by importance score)

  R1. Literature-Search-R
      - Independent queries derived from manuscript abstract + claim paraphrases
      - DIFFERENT search strategy than writer: prefer recent (last 24mo), prefer high-citation,
        prefer contradicting-evidence-discovery prompts
      - Outputs paper_list_R<i>.json, possibly overlapping with writer's set but not constrained to it

  R2. GraphBuilder-R
      - Same paper-extractor agent runs against R_i's paper list
      - Outputs kg_reviewer_<i>.yaml (reviewer-tier wing)

  R3. PR-Hypothesizer-R
      - Re-derives candidate claims about each headline-claim-topic from R_i's KG only
      - Outputs claim_redrivation_R<i>.yaml

  R4. PR-Confrontation
      - For each headline claim C in writer's manuscript:
          - Query R_i's KG for nodes supporting C (anchors_R)
          - Query R_i's KG for nodes contradicting C (counter_anchors_R)
          - Cross-check: does writer's anchor for C appear in R_i's KG?
              - If yes → confirmation
              - If no but R_i has support → independent confirmation
              - If R_i has counter → contestation
              - If R_i has neither → unsupported-by-R
      - Emits review_R<i>.json
```

### 5.2 Reviewer verdict schema

```yaml
reviewer_id: reviewer_1
reviewer_kg: vedix_kg__reviewer__1__<job_id>
n_papers_independently_pulled: 87
overlap_with_writer_set: 23
new_to_reviewer: 64

per_claim:
  - claim_id_in_manuscript: m07.claim01
    claim_paraphrase: "HOMO-LUMO gap correlates with DA rate (r=0.78)"
    verdict: confirmed | independently_confirmed | contested | unsupported_by_R | partial

    # if confirmed/independently_confirmed:
    supporting_anchors_R:
      - {node_id: jones2022.claim04, paper: jones2022, agreement: full}
      - {node_id: liu2023.claim02,   paper: liu2023,  agreement: weaker_effect}

    # if contested:
    counter_anchors_R:
      - {node_id: kim2024.claim03, paper: kim2024,
         contradiction: "Kim 2024 reports r=0.34 for electron-rich dienophiles — opposite trend within scope"}

    # if unsupported_by_R:
    investigation_notes: "Reviewer searched 87 papers; no source either supporting or contradicting found within recency window."

n_confirmed: 6
n_independently_confirmed: 3
n_contested: 1
n_unsupported_by_R: 0
stance_score: 8.2   # /10
```

### 5.3 Reviewer-KG → project-KG merge

After all reviewers finish, their KGs merge into the project-tier KG via `lattice_merger.merge_reviewer_kgs()`:

- **Papers**: dedup by DOI; raw stored once in `~/.vedix/projects/<id>/raw_cache/`; structured fragments preserved per-reviewer (provenance: which reviewer pulled which paper).
- **Concepts**: lattice merger runs same auto-merge-at-confidence>0.9 rule; conflicts surface to user.
- **Claims**: each Claim node carries `discovered_by: [writer | reviewer_1 | reviewer_2 | ...]`.
- **Cross-track edges**: explicit `confirms`, `contests`, `independently_supports` edges added between writer-KG claims and reviewer-KG claims.

### 5.4 Contested-claim policy

Three policies, picked at setup time:

| Policy | Behavior |
|---|---|
| **strict** | Contested claims block manuscript finalization until writer addresses (rewrite, hedge, or counter-argue with new sources) |
| **mediation** | Mediator agent reads writer's anchor + reviewer's counter; proposes a reconciliation; writer can accept or reject |
| **disclose** | Manuscript ships with contested claims marked + a "Reviewer Contestations" appendix showing disagreement transparently |

Default (matching parent spec's pre-registration hard-gate posture): **strict** for headline claims (top-10 by importance), **disclose** for non-headline.

**Importance score** (deterministic):

```
importance(claim) = 0.4 * mentions_in_manuscript          # how many sentences anchor to it
                  + 0.3 * downstream_anchor_count          # how many other claims depend on it
                  + 0.2 * appears_in_abstract              # boolean → 0 or 1
                  + 0.1 * appears_in_conclusion            # boolean → 0 or 1
```

Top-10 by this score = "headline claims" for the contested-claim policy.

---

## 6. Persistence + MemPalace tier mapping

### 6.1 Tier lifecycle

| Tier | MemPalace wing | Lifetime | Cleared by |
|---|---|---|---|
| **Job-tier (writer)** | `vedix_kg__job__<job_id>` | Job + 30 days post-completion (audit window) | `vedix kg gc --older-than 30d` |
| **Job-tier (reviewer N)** | `vedix_kg__reviewer__<N>__<job_id>` | Same as writer's job-tier; merges into project tier on review completion | Automatic on merge |
| **Project-tier** | `vedix_kg__project__<project_id>` | Persists until `vedix project delete` | User explicit |
| **Niche-tier** | `vedix_kg__niche__<discipline>__<sub_niche>` | Read-only; updated by scheduled `rebuild_niche` job | Maintainers / scheduled |

### 6.2 Niche derivation

Niches are a **closed list** maintained at `plugins/vedix/templates/niches.yaml`. Examples (the file ships with ~60 niches across the 8 disciplines):

```yaml
niches:
  chemistry:
    - photochemistry
    - organometallic_catalysis
    - polymer_synthesis
    - electrochemistry
    - computational_chemistry
  biology:
    - single_cell_genomics
    - structural_biology
    - microbiome
    - developmental_biology
    - evolutionary_biology
  medicine:
    - oncology_clinical_trials
    - cardiology_intervention
    - infectious_disease_epidemiology
    - psychiatry_outcomes
  physics:
    - quantum_information
    - condensed_matter_theory
    - particle_physics
    - general_relativity
  # ...
```

The orchestrator picks the niche at preflight via a small classifier (`niche_classifier.py`): given `{discipline, topic_text}`, embed the topic + each candidate sub-niche label and return the top-1 by cosine similarity. If no niche scores above 0.5, fall back to a `<discipline>/general` niche.

Users extend the list via `vedix kg add-niche <discipline>/<niche_name>`; this appends to a local `~/.vedix/niches.local.yaml` that merges with the bundled list.

A new project starting in `chemistry/photochemistry` mounts the matching niche-tier wing read-only at preflight. The niche lattice provides a starter terminology baseline. The niche `top_claims.json` provides high-confidence cross-project canonical claims.

User project KG never overwrites niche-tier — niche is *derived* from project tiers via scheduled `rebuild_niche` job (nightly on SaaS, on-demand locally via `vedix kg rebuild-niche <name>`).

### 6.3 Cache invalidation

| Cache | Key | Invalidated by |
|---|---|---|
| Paper KG fragment | `paper_id` + `extractor_model_version` | Re-extraction with newer extractor |
| Allowed-set per paragraph | hash of `paragraph_topic + hypothesis_anchors + kg_revision_id` | KG revision change |
| Reviewer verdict | hash of `reviewer_kg_revision + writer_claim_anchors` | Either side updates |

### 6.4 Backup + portability

```bash
vedix kg export --project <id> --to ./project_kg_export.tgz
vedix kg import --from ./project_kg_export.tgz --as-project <new_id>
```

Carry-your-knowledge-between-machines surface — workstation ↔ SaaS.

---

## 7. Error handling + edge cases

### 7.1 Extraction failures

| Failure | Trigger | Recovery |
|---|---|---|
| Schema violation | Extractor returns YAML that fails pydantic validation | Retry once with stricter prompt + schema-as-system-message. On second failure → `extraction_failed/`; counted in `kg_summary.yaml`. |
| Truncated extraction | Paper > 100k tokens; context exceeded | Section-by-section extraction: split raw text by section headers, extract each, merge fragments. ~3× cost. |
| OCR / encoding garbage | pdfminer returned mostly-noise for image-PDF | Mark `raw_unusable`; surface to user with choice: skip / OCR-via-tesseract / fetch better source. |
| Paywalled / 403 | MCP download returned access denied | Mark `paper_not_accessible`; preserve metadata; surface count. User may `vedix kg add-paper <doi> --pdf <path>`. |
| LLM rate-limit / 5xx | Provider chain fallback exhausted | Block-level retry with exponential backoff (v3.0 dispatch infrastructure). |
| Unsupported language | Detected language not in {EN, RU, ES, DE, FR, ZH, JA} | Skip extraction; preserve raw with `lang=unsupported`; mention in `kg_summary.yaml`. |

### 7.2 Verifier failures (write-time)

| Failure | Recovery |
|---|---|
| `cite` entailment fails | Writer agent told "your sentence claims X but anchor's verbatim quote says Y; rewrite or change anchor". Max 3 retries. After 3, switch bucket (try `synthesize` with multiple anchors, or `speculate` with explicit hedge + user approval). |
| `synthesize` path-check fails | "Your synthesis is a trivial restatement of anchor[0]" or "path doesn't logically connect". Writer rewrites or downgrades to `cite` against a single stronger anchor. |
| `speculate` not pre-authorized + interactive mode disabled | Hard block. Pipeline pauses, `AskUserQuestion` fires with proposed speculation + rationale. User: authorize / reject / amend. |
| Verifier provider timeout | Sentence flagged `verification_pending`. Manuscript still emits draft, sentence yellow-flagged. Cleanup pass at end of manuscript-writer phase: re-run verifier on every `verification_pending` sentence with a longer timeout + fallback provider chain. Sentences that fail the cleanup pass enter the same retry/bucket-switch/block path as any other failing sentence (per row 1 of this table). |

### 7.3 Lattice conflict resolution UX

```
[Lattice Conflict — Batch 3 of 7]

Paper smith2024 introduces concept "frontier orbital energy"
Project lattice already has  "HOMO-LUMO gap" (used in 17 papers)

Are these the same concept?
  [A] Yes, merge — adopt "frontier orbital energy" as canonical, "HOMO-LUMO gap" becomes alt_label
  [B] Yes, merge — keep "HOMO-LUMO gap" as canonical, "frontier orbital energy" becomes alt_label
  [C] No — they are distinct concepts (record as `related` in the lattice)
  [D] Maybe — defer; ask me again when more papers are extracted
```

Batched at end-of-GraphBuilder so the user sees all conflicts in one prompt. Up to ~10 conflicts per typical 150-paper job.

### 7.4 Speculation gate UX

| Mode | Behavior |
|---|---|
| **Batch (default)** | All proposed speculations collected during writing; at end of each section, user sees list with rationale + bucket-classification reason; checks each: `authorize` / `reject` / `amend`. |
| **Live** | Each proposed speculation triggers immediate `AskUserQuestion`; pipeline pauses until answered. For hands-on sessions. |

Toggle: `vedix new --speculation-gate live | batch`.

### 7.5 MemPalace contention / concurrency

- **Per-paper drawers**: write-locked by `paper_id`; first writer wins, second reads + skips.
- **Lattice**: serialized via single `lattice_merger` queue per project; second job's lattice changes batched, applied when first releases lock.
- **Cross-track edges**: written by reviewer-track only AFTER all writer-track is complete; no contention by construction.

### 7.6 KG corruption / recovery

KG fully reconstructible from `raw/` + original extractor prompts.

```bash
vedix kg verify --job <job_id>            # check every claim's verbatim_quote against raw_pointer byte_range
vedix kg rebuild --job <job_id> --from raw  # re-extract from raw; preserve user-confirmed lattice merges
```

---

## 8. Testing strategy

### 8.1 Unit tests (deterministic)

| Layer | Path | Approach |
|---|---|---|
| Schema | `tests/sgca/test_schema.py` | Pydantic validate valid + invalid YAML fragments |
| `kg_store` | `tests/sgca/test_kg_store.py` | In-memory SQLite MemPalace fixture; drawer/tunnel round-trip; lattice merge logic |
| `paragraph_planner` | `tests/sgca/test_planner.py` | Synthetic KG with known relevance ground-truth |
| `claim_verifier` (cite) | `tests/sgca/test_verifier_cite.py` | Hand-curated (sentence, anchor) pairs labeled entailed/contradicts/stronger |
| `claim_verifier` (synthesize) | `tests/sgca/test_verifier_synthesize.py` | Synthetic 2-anchor cases |
| `claim_verifier` (speculate) | `tests/sgca/test_verifier_speculate.py` | Pre-authorized vs not; live mode AskUserQuestion mock |
| `lattice_merger` | `tests/sgca/test_lattice_merger.py` | Auto-merge >0.9; conflict surface <0.9 |

### 8.2 Faithfulness benchmark (gold-standard)

Curated gold-set: ~50 papers across the niche-coverage benchmark, each with hand-extracted KG fragments by 2 domain experts (one chemistry, one biology — covers the niches).

For every extractor model + version:

```
Per paper p in gold-set:
  auto_kg = paper-extractor(p)
  gold_kg = experts(p)
  metrics:
    - claim_precision = |auto_claims ∩ gold_claims| / |auto_claims|
    - claim_recall    = |auto_claims ∩ gold_claims| / |gold_claims|
    - claim_f1
    - verbatim_quote_exact_match_rate   ← every auto claim's quote must literally appear in raw
    - byte_range_accuracy               ← quote_byte_range must point to actual quote
    - lattice_concept_overlap           ← Jaccard against gold lattice
```

**Production gate**: claim_f1 ≥ 0.85 AND verbatim_quote_exact_match_rate = 1.0. Verbatim match is a hard constraint, never soft.

Stored at `tests/sgca/gold_set/` (50 papers × 2 expert extractions, committed with provenance).

### 8.3 Verifier accuracy benchmark

Curated set: ~500 (sentence, anchor) pairs hand-labeled `entailed | contradicts | stronger | weaker | unrelated`.

```
Per pair:
  verifier_verdict = claim_verifier.judge(sentence, anchor)
  metrics:
    - entailment_accuracy
    - false_negative_rate   ← entailed sentences wrongly rejected (over-strict)
    - false_positive_rate   ← unsupported sentences wrongly accepted (security failure)
```

**Production gate**: false_positive_rate < 2%. False negatives are OK (trigger rewrites).

### 8.4 Reviewer-track integration tests

End-to-end synthetic scenario: deliberately falsified manuscript with 10 known-wrong claims:

```
Per scenario:
  reviewer_track runs against falsified manuscript
  metrics:
    - contested_recall = # of seeded-wrong claims flagged contested
    - false_contest_rate = # of correct claims wrongly flagged contested
```

**Production gate**: contested_recall ≥ 0.8, false_contest_rate < 5%.

### 8.5 KG reconstructibility test

```python
def test_kg_reconstructible_from_raw(real_job_id):
    original_kg = load_kg(job_id=real_job_id)
    rebuilt_kg  = kg_rebuild_from_raw(job_id=real_job_id)
    for claim in original_kg.claims():
        raw_text = open(claim.raw_pointer.text).read()
        actual = raw_text[claim.quote_byte_range[0]:claim.quote_byte_range[1]]
        assert actual == claim.verbatim_quote, f"quote drift for {claim.id}"
```

Run on every production run as final integrity check before manuscript ships.

### 8.6 Performance regression suite

| Metric | Target | Measured how |
|---|---|---|
| GraphBuilder wall-clock (first run, 150 papers, 8-wide) | < 25 min | Bench harness on Xeon 8368 + cheap-provider BYOK chain |
| Verifier wall-clock per sentence | < 5 s | Per-sentence ledger timestamps |
| Allowed-set computation | < 2 s per paragraph | Profiled in CI |
| KG storage growth | < 1 GB per 100 papers (incl. raw) | `du -sh ~/.vedix/palace/...` after fixture runs |

### 8.7 Out of scope for testing

- LLM's internal "thinking" during extraction — we test only output's faithfulness to raw.
- Whether the paper's claims are scientifically true — we test fidelity-of-paraphrase, not truth-of-claim.
- Whether the chosen anchor is the *best* anchor — only that the sentence is entailed by it.

---

## 9. Relationship to existing v3.0 rigor tracks

SGCA does NOT replace §§4.1–4.7. It supplements them by closing the write-time gap they leave open.

| Existing track | What it does | What SGCA adds |
|---|---|---|
| §4.1 Failure-mode learning | HDBSCAN cluster of pipeline failure corpus | Adds "extraction-faithfulness-failure" cluster class |
| §4.2 Citation graph analytics | Statistical signals over reference list | No change — runs orthogonally on the KG-derived bib |
| §4.3 Counterfactual citation probing | Decoy injection + LLM-judge — does claim still hold? | Becomes redundant for `cite`-bucket sentences (verifier already grounds them); still useful for `synthesize` paths |
| §4.4 Adversarial multi-pass review | Same reviewer, opposing stances | Upgraded: independent reviewers with independent evidence (this spec §5) |
| §4.5 Semantic revision diff | Embedding cosine between revisions | No change — runs on manuscript text |
| §4.6 Pre-registration replay | Hard-gate + audit | No change — runs on results, not claims |
| §4.7 Provenance ledger | Per-sentence agent/model tags | Extended: per-sentence anchor IDs + verifier verdict in the ledger |

---

## 10. Open questions deferred to implementation

None blocking. All design decisions locked in §§1–8. Implementation choices to be settled in the writing-plans phase:

- Whether `claim_verifier` runs in-process or as a separate worker (perf tuning)
- Exact embedding model for allowed-set retrieval (likely `multilingual-e5-large` matching §5.3 of parent spec)
- Whether reviewer parallelism is 2 or 3 (parent-spec Q5 — already gated)
- HNSW vs. flat-index for KG retrieval (depends on KG size; both fit in MemPalace SQLite)

---

## 11. Out of scope (post-v3.0, deferred)

- **Cross-language KG fusion** (writer-KG in EN merged with reviewer-KG in RU for the same paper): possible but adds translation-confidence-tracking complexity.
- **Image / figure extraction** into the KG: figures are referenced by caption only at v3.0; full figure-content extraction (chart values, microscopy annotations) is a future track.
- **Equation extraction** as first-class nodes: equations are preserved verbatim in claim/method quotes but not parsed into AST-level nodes.
- **Real-time collaborative KG editing** (multiple authors editing the same KG concurrently): falls under §5.11 collab; the KG can be Yjs-backed but the verifier doesn't gate concurrent edits.
- **KG-aware peer-review of OTHER authors' papers** (a "review someone else's preprint with SGCA"): natural extension once the SaaS exposes review-only entry points; out of scope here.
