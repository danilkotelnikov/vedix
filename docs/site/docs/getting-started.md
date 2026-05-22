# Getting started &mdash; your first job

This walkthrough takes a fresh install from zero to a venue-ready manuscript
in about 30 minutes. We'll use the simplest possible pipeline: a synthetic
linear-regression experiment targeted at the default preprint template.

## 1. Open your assistant

Open Claude Code, Codex CLI, or Gemini CLI &mdash; whichever you installed
Vedix into. From here on, every command in this guide runs inside that
assistant's prompt.

## 2. Start a job

```text
/vedix new
```

A nine-field setup form appears. Fill it out:

| Field | Example |
| --- | --- |
| Topic | `Does the number of training epochs correlate with test-set R^2 on a synthetic regression?` |
| Discipline | `computer_science` |
| Language | `en` |
| Venue | `preprint` |
| Hypothesis style | `exploratory` |
| Experiment type | `computational` |
| Primary metric | `pearson_r` |
| Expected direction | `increase` |
| Tolerance | `0.05` |

Submit. Vedix prints a job ID like `job_2026_05_22_x7k9`.

## 3. Watch the pipeline run

Each phase streams progress to your assistant:

1. **Literature search** &mdash; queries Semantic Scholar, OpenAlex, arXiv,
   PubMed.
2. **Hypothesis design** &mdash; locks the hypothesis into a pre-registration
   record before any experiment runs.
3. **Experimentation** &mdash; generates and runs Python code; produces
   `results.csv` and any companion artifacts.
4. **Claim audit** &mdash; the numerical-claim auditor reads `results.csv` and
   refuses to let the manuscript cite a number that disagrees with it.
5. **Rigor passes** &mdash; the seven rigor mechanisms run; the provenance
   ledger records every assertion's source.
6. **Typesetting** &mdash; the publisher engine renders the manuscript in
   your chosen venue's template.

Total wall time: typically 20&ndash;40 minutes on a modern machine with a
fast BYOK provider.

## 4. Read the output

When the pipeline finishes, your manuscript lives at:

```text
~/.vedix/jobs/job_2026_05_22_x7k9/
  manuscript.pdf
  manuscript.tex
  results.csv
  rationale.md
  preregistration.json
  provenance_ledger.json
  ai_disclosure.md
```

Open `manuscript.pdf`. Every numerical claim in the prose can be traced back
to a row in `results.csv` via `provenance_ledger.json`. Every citation can be
inspected with `vedix audit-citations job_2026_05_22_x7k9`.

## 5. Iterate

Re-run with a different venue:

```text
/vedix retypeset job_2026_05_22_x7k9 --venue elsevier:cell-reports-medicine
```

Or change a parameter and re-run from the experiment phase:

```text
/vedix continue job_2026_05_22_x7k9 --from experiment --param epochs=200
```

## Next steps

- Add your own BYOK provider: [BYOK providers](./byok.md)
- Switch to Russian + GOST: [Languages](./languages.md)
- Try a journal venue: [Publisher templates](./publishers.md)
- Learn what each rigor track does: [Rigor tracks](./rigor-tracks.md)

## Troubleshooting

??? failure "`/vedix` is not recognized"
    The plugin isn't registered. Rerun the installer; make sure you select
    the agent you're actually using.

??? failure "Pipeline hangs at literature search"
    Most often a network or BYOK-key issue. Run `vedix doctor` to print the
    configuration the plugin sees. The doctor command pings every registered
    MCP and BYOK provider in sequence.

??? failure "`models/register_classifier.bin` not found"
    The one-time model download failed or was skipped. Run
    `vedix download-models` to retry.
