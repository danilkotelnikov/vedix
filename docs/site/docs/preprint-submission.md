# Pre-print submission

Vedix can submit a finished manuscript to a preprint server in one command.
Five adapters ship in the box:

| Server | Code | Auth |
| --- | --- | --- |
| arXiv | `arxiv` | API key |
| bioRxiv | `biorxiv` | API key |
| OSF Preprints | `osf` | OAuth token |
| SSRN | `ssrn` | API key |
| Generic SWORD-v2 server | `sword` | Basic auth |

## Usage

```text
/vedix submit-preprint job_2026_05_22_x7k9 --server arxiv
```

Vedix takes the manuscript, attached source bundle, AI-disclosure paragraph,
and pre-registration record, packages them per the adapter's contract, and
returns the assigned preprint ID. The provenance ledger records the
submission timestamp + the returned DOI/URL.

## Configuring credentials

Set environment variables or place them in `~/.vedix/secrets.yaml`:

```yaml
preprint:
  arxiv:
    api_key: …
  biorxiv:
    api_key: …
  osf:
    oauth_token: …
  ssrn:
    api_key: …
  sword:
    base_url: https://my-repo.example.org/sword
    username: …
    password: …
```

## Errata + replacements

Most servers allow author-driven replacement after submission. Vedix exposes:

```text
/vedix replace-preprint <preprint_id> <new_job_id>
```

which uploads the new revision as a versioned replacement, preserving the
original DOI.
