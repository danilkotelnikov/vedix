# Web UI

The Vedix web UI is a React 19 + Vite + Tailwind application that fronts the
Vedix.ai SaaS. It shipped as part of Block 9 of the v3.0 release.

## Surfaces

- **Sign-in** &mdash; email + magic link.
- **Job dashboard** &mdash; list of recent jobs with state, provenance, and
  cost.
- **Job form** &mdash; the same nine-field setup form available in the CLI.
- **Progress stream** &mdash; SSE-driven live pipeline view.
- **Manuscript preview** &mdash; react-pdf renders the LaTeX-built PDF
  inline.
- **Provenance tooltips** &mdash; hover any sentence to see its agent +
  model + retrieval context.
- **Providers** &mdash; configure BYOK chains and reorder fallback.
- **Cost ledger** &mdash; per-job, per-provider, per-tier cost breakdown.
- **Collaborative editor** &mdash; Yjs-backed real-time editing with
  presence cursors.

## Running locally

```bash
cd plugins/vedix/web
npm install
npm run dev
```

The dev server reads `VITE_VEDIX_API_URL` from `.env.local`; default is
`http://localhost:8000`.

## Deployment

The web UI is shipped as a Docker image (`plugins/vedix/web/Dockerfile`)
and is served behind the same nginx that fronts the SaaS API.
