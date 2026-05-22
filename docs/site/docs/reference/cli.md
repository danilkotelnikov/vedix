# CLI reference

The `vedix` CLI is available after install at `~/.vedix/venv/bin/vedix`
(Linux/macOS) or `~/.vedix/venv/Scripts/vedix.exe` (Windows). The installer
adds it to your `PATH`.

Inside Claude Code, Codex CLI, or Gemini CLI, the same commands are exposed
as `/vedix <subcommand>`.

## Subcommands

| Command | Purpose |
| --- | --- |
| `vedix new` | Start a job (interactive form) |
| `vedix submit` | Start a job from a YAML/JSON config |
| `vedix status <job_id>` | Inspect job state |
| `vedix tail <job_id>` | Tail the progress stream |
| `vedix continue <job_id> --from <phase>` | Resume from a phase |
| `vedix retypeset <job_id> --venue <code>` | Re-render in another venue |
| `vedix audit-citations <job_id>` | Run counterfactual probe |
| `vedix submit-preprint <job_id> --server <code>` | Push to preprint |
| `vedix replace-preprint <preprint_id> <new_job_id>` | Replace |
| `vedix doctor` | Print environment + plugin diagnostics |
| `vedix download-models` | Re-pull the register classifiers |
| `vedix list-venues` | Print the 23-venue registry |
| `vedix list-providers` | Print the BYOK provider chain |
| `vedix migrate-v2` | Migrate a v2 palace into v3 layout |

## Global flags

- `--host {claude,codex,gemini,auto}` &mdash; force a host
- `--palace <path>` &mdash; override `~/.vedix/`
- `--quiet`, `--verbose`, `--json`
- `--no-network` &mdash; offline-only mode (no SaaS, no preprint, no
  external BYOK)

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Generic failure |
| 2 | Bad arguments |
| 10 | Pipeline failed before manuscript draft |
| 11 | Rigor track flagged blocker |
| 12 | Numerical claim audit failed |
| 13 | Provenance ledger could not close |
| 20 | Network / SaaS error |
| 30 | Configuration error |
