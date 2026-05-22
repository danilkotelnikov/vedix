# Federated palace

A palace is a Vedix workspace: a folder of jobs, configurations, classifiers,
and the rigor ledger that connects them. The federated palace is a
multi-user palace hosted on Vedix.ai or self-hosted on your infrastructure.

## Shared palace REST API

A read/write REST surface at `https://api.vedix.ai/v1/palace/` exposes:

| Endpoint | Verb | Purpose |
| --- | --- | --- |
| `/drawers` | GET/POST | List or create drawers (job collections) |
| `/drawers/{id}/acl` | GET/PUT | Read or update per-drawer ACL |
| `/drawers/{id}/jobs` | GET | List jobs in a drawer |
| `/drawers/{id}/jobs/{job_id}` | GET | Fetch a job's manifest |
| `/drawers/{id}/yjs` | WS | Open the collaborative editing channel |

## ACL model

Each drawer has an ACL of `(principal, permission)` rows where `principal` is
a user ID or group ID and `permission` is one of `read`, `write`, `admin`.
`admin` can re-share; `write` includes `read`; `read` is read-only access to
manuscripts, results.csv, rationale.md, prereg, and provenance ledger.

## Collaborative editing

The web UI uses Yjs over the `/yjs` WebSocket channel. Multiple users can
edit a manuscript concurrently; cursors are presence-broadcast; snapshots
are persisted to the palace database every 5 minutes.

## Self-hosting

The palace ships as a docker-compose bundle in
`plugins/vedix/saas/`. You can run a private federated palace on a single VM
and point your team's clients at it via `VEDIX_PALACE_URL`.
