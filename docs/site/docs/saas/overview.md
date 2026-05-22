# SaaS overview

Vedix.ai is the hosted version of Vedix. It runs the same pipeline as the
open-source CLI, but on a managed job queue with the 9 MCPs preinstalled,
the register classifiers preloaded, and a web UI.

## Tiers

| Tier | Throughput | Concurrent jobs | Storage | Price |
| --- | --- | --- | --- | --- |
| Free | 5 jobs / month | 1 | 5 GB | 0 |
| Solo | 50 jobs / month | 2 | 100 GB | 19 USD / month |
| Team | 500 jobs / month | 8 | 1 TB | 99 USD / month |
| Org | unlimited | 32 | 10 TB | contact sales |

Every tier &mdash; including Free &mdash; gets every feature: all 9 MCPs,
all 23 publisher templates, all 7 languages, all 7 rigor mechanisms, web UI,
IDE plugins, federated palace, collaborative editing, preprint adapters.
Paid tiers buy throughput, concurrency, and storage; they don't unlock
gated features.

## Payment methods

- **International**: Stripe (cards, Apple Pay, Google Pay), PayPal.
- **Russia / EEU**: YuKassa (cards, SBP, Yandex Pay, SberPay), CloudPayments.
- **Crypto**: BTC, ETH, USDT (TRC-20, ERC-20).
- **Boosty / Patreon**: subscription mirror.

The full payment integration is in
`plugins/vedix/saas/payments/`.

## Infrastructure

- API: FastAPI behind nginx, deployed via docker-compose.
- Job queue: arq + Redis.
- DB: Postgres 16 with alembic migrations.
- Object store: S3-compatible (default: Cloudflare R2).
- MCP fleet: hosted on per-tenant pods, with rate limits per tier.

## Self-hosting

The full stack ships as a docker-compose bundle. See
`plugins/vedix/saas/docker-compose.yml` for the reference deployment.
