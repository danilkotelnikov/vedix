# Rigor tracks

Seven rigor mechanisms run at fixed points in the pipeline. Each one is a
small, opinionated audit; together they make Vedix's output structurally
harder to fake than a hand-edited draft.

## 1. Failure-mode learning

HDBSCAN-clusters Vedix's own historical failure traces and turns the largest
clusters into pre-flight checks for new jobs. Catches recurring issues like
`"hypothesis depends on a variable the experiment never measured"` before
the experiment runs.

## 2. Citation graph analytics

Computes three metrics on the reference list: Gini freshness (concentration
of citation years), density (citations per page weighted by section), and
self-citation ratio. Out-of-band values surface in the rigor report.

## 3. Counterfactual citation probing

For each citation, asks an LLM judge two questions:

1. If I replace this citation with a plausible decoy, does the sentence's
   meaning change?
2. If yes, by how much?

Decorative citations &mdash; ones that don't constrain the sentence's
truth-content &mdash; are flagged.

## 4. Adversarial multi-pass review

The same reviewer is run against the manuscript twice with opposing stances
(steelman + break). Agreement between the two passes is a robustness signal;
disagreement marks a fragile claim for review.

## 5. Semantic revision diff

Between two manuscript revisions, embeds every claim sentence and reports
pairs whose cosine similarity dropped below a threshold &mdash; ie, claims
whose meaning silently inverted during editing.

## 6. Pre-registration replay

Before the experiment runs, Vedix commits a pre-registration record
(hypothesis, primary metric, expected direction, tolerance). After the
experiment, an auditor replays the prereg against the actual results and
flags any silent post-hoc adjustments.

## 7. Provenance ledger + auto-disclosure

Every sentence in the final manuscript carries a tag in
`provenance_ledger.json`: which agent wrote it, which model, against which
context. The auto-disclosure pass converts those tags into a journal-ready
AI-disclosure paragraph in the language of your venue.

## When each track runs

| Track | Phase |
| --- | --- |
| Failure-mode learning | Pre-flight |
| Citation graph analytics | After literature search |
| Counterfactual citation probing | After draft |
| Adversarial multi-pass review | After draft |
| Semantic revision diff | Between revisions |
| Pre-registration replay | Before + after experiment |
| Provenance ledger | Throughout |
