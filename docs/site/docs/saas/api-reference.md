# SaaS API reference

Base URL: `https://api.vedix.ai/v1`

All endpoints require a bearer token: `Authorization: Bearer <token>`. Get
one from `https://app.vedix.ai/settings/tokens`.

## Jobs

### Create job

`POST /api/jobs`

```json
{
  "topic": "Does training time correlate with R^2?",
  "discipline": "computer_science",
  "language": "en",
  "venue": "preprint",
  "hypothesis_style": "exploratory",
  "experiment_type": "computational",
  "primary_metric": "pearson_r",
  "expected_direction": "increase",
  "tolerance": 0.05
}
```

Response: `201 Created`

```json
{ "job_id": "job_2026_05_22_x7k9", "state": "queued" }
```

### Get job status

`GET /api/jobs/{job_id}`

Response:

```json
{
  "job_id": "job_2026_05_22_x7k9",
  "state": "running",
  "phase": "experiment",
  "progress": 0.62,
  "eta_seconds": 540
}
```

States: `queued`, `running`, `done`, `failed`, `cancelled`.

### Stream progress (SSE)

`GET /api/jobs/{job_id}/stream`

Server-sent events with named event types: `phase`, `progress`, `log`,
`done`, `error`.

### Download artifact

`GET /api/jobs/{job_id}/artifacts/{name}`

`name` is one of `manuscript.pdf`, `manuscript.tex`, `results.csv`,
`provenance_ledger.json`, `ai_disclosure.md`, `preregistration.json`.

## Palace

### List drawers

`GET /api/palace/drawers`

### Drawer ACL

`GET /api/palace/drawers/{id}/acl`
`PUT /api/palace/drawers/{id}/acl`

### Collaborative editing

`WS /api/palace/drawers/{id}/yjs`

A Yjs WebSocket channel. Bind your Y.Doc; the server persists snapshots
every 5 minutes.

## Pre-print

### Submit

`POST /api/preprint/{server}/submit`

`server` is one of `arxiv`, `biorxiv`, `osf`, `ssrn`, `sword`.

Body:

```json
{ "job_id": "job_2026_05_22_x7k9" }
```

Response:

```json
{ "preprint_id": "2605.12345", "url": "https://arxiv.org/abs/2605.12345" }
```

## Errors

All errors return:

```json
{ "error": { "code": "INVALID_VENUE", "message": "venue not in registry" } }
```

with the appropriate HTTP status (400, 401, 403, 404, 409, 429, 500).
