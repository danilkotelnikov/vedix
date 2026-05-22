# IDE plugins

Vedix ships first-class plugins for VS Code and the JetBrains family
(IntelliJ IDEA, PyCharm, WebStorm, GoLand, Rider). Both plugins talk to the
Vedix.ai SaaS over the same JWT-authenticated API; offline they fall back to
the local CLI.

## VS Code

Install from the Marketplace:

```text
ext install vedix.vedix
```

Or sideload the bundled `.vsix`:

```bash
code --install-extension plugins/vedix/ide/vscode/vedix-*.vsix
```

Features:

- **Vedix: New manuscript** command palette action.
- **Progress panel** &mdash; SSE-driven phase view for the active job.
- **Status bar** &mdash; current job + phase + ETA.
- **Citation hover** &mdash; hover any `\cite{…}` to see the cited paper's
  metadata and counterfactual probe verdict.

## JetBrains

Install from the JetBrains Marketplace, or sideload:

```bash
# IntelliJ: File → Settings → Plugins → Install Plugin from Disk
plugins/vedix/ide/jetbrains/build/distributions/vedix-*.zip
```

Features:

- Tool window for the active job.
- New-manuscript action accessible from the search-everywhere palette.
- The same SSE progress view as the VS Code plugin.

## Offline fallback

When `VEDIX_SAAS_URL` is unreachable, both plugins shell out to the local
`vedix` CLI. You can pin to local-only mode with
`VEDIX_PLUGIN_MODE=local-cli`.
