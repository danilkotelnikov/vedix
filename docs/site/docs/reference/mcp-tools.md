# MCP tools reference

Vedix ships 9 MCP servers. The installer registers all of them in your host
agent's MCP config. Each is also available individually on the Vedix.ai SaaS.

| MCP | Module | Purpose |
| --- | --- | --- |
| `vedix.orchestrator` | `plugins/vedix/orchestrator` | Pipeline runner |
| `vedix.byok` | `plugins/vedix/byok` | Provider chain |
| `vedix.rigor` | `plugins/vedix/rigor` | 7 rigor mechanisms |
| `vedix.net_new` | `plugins/vedix/net_new` | Numerical audit, rationale, codebase-aware mode |
| `vedix.discriminator` | `plugins/vedix/discriminator` | Hybrid register classifier |
| `vedix.locale` | `plugins/vedix/locale` | 7 first-class languages |
| `vedix.preprint` | `plugins/vedix/preprint` | 5 preprint adapters |
| `vedix.publisher` | `plugins/vedix/publisher` | 23-venue template engine |
| `vedix.sgca` | `plugins/vedix/sgca` | Source-grounded claim architecture |

## Tool surface

Each MCP exposes a small set of tools. The full schema is published in
`gemini-extension.json` and the per-host plugin manifests; the table below
lists representative tools per MCP.

### `vedix.orchestrator`

- `start_pipeline(job_id, config)`
- `get_phase(job_id)`
- `cancel(job_id)`
- `list_jobs()`

### `vedix.byok`

- `list_providers()`
- `set_chain(task, providers)`
- `current_chain(task)`

### `vedix.rigor`

- `run_track(name, job_id)` &mdash; runs one of the seven tracks
- `run_all(job_id)`
- `report(job_id)`

### `vedix.net_new`

- `numerical_audit(manuscript, results_csv)`
- `write_rationale(job_id)`
- `analyze_codebase(path)`

### `vedix.discriminator`

- `classify(text, kind)` &mdash; kind in {retrieval, style}
- `embed(text)`

### `vedix.locale`

- `format_reference(record, code)`
- `apply_typography(text, code)`

### `vedix.preprint`

- `submit(server, job_id)`
- `replace(server, preprint_id, new_job_id)`
- `status(server, preprint_id)`

### `vedix.publisher`

- `list_venues()`
- `render(job_id, venue)`
- `parity_check(latex_path, docx_path)`

### `vedix.sgca`

- `register_claim(sentence, source)`
- `verify_claim(sentence)`
- `ledger(job_id)`

## Calling from your own client

The MCPs follow the Model Context Protocol spec, so any MCP-aware client
(Claude Code, Codex CLI, Gemini CLI, Continue, Cline, custom client) can
call them after registration. See
`docs/site/docs/install.md` for registration paths per host.
