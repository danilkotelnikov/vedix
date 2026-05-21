"""Block-9 / Block-10 / Block-11 integration hooks.

These modules expose the orchestrator-side surface that future net-new
UIs and external integrations plug into:

* `webui_events` — Server-Sent-Events bus consumed by the web UI (B9).
* `ide_protocol` — JSON-RPC schema for the VS Code / JetBrains plugins (B10).
* `preprint_submit` — CLI scaffolding for arXiv / bioRxiv / OSF / SSRN (B11).
"""
