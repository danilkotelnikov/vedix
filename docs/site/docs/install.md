# Install

Vedix runs as a plugin inside Claude Code, Codex CLI, or Gemini CLI. The
bootstrap installer detects which agent is on your `PATH` and registers the
plugin and its MCP fleet against that host's configuration.

## One-line install

=== "Linux / macOS"
    ```bash
    curl -fsSL https://vedix.ai/install.sh | bash
    ```

=== "Windows (PowerShell 5.1+)"
    ```powershell
    iwr -useb https://vedix.ai/install.ps1 | iex
    ```

The installer is interactive: it lists every supported agent it finds on your
machine and lets you opt in or out per agent. Choose any subset; you can rerun
the installer later to add more.

## What the installer does

1. Clones `vedix/vedix` to `~/.vedix/repo`.
2. Creates a Python 3.11+ virtualenv at `~/.vedix/venv`.
3. Installs the plugin into the selected agent's plugin directory:
    - Claude Code: `~/.claude/plugins/vedix/`
    - Codex CLI: `~/.codex/plugins/vedix/`
    - Gemini CLI: `~/.gemini/extensions/vedix/`
4. Registers the 9 MCP servers (orchestrator, byok, rigor, net-new,
   discriminator, locale, preprint, publisher, sgca) against each host's MCP
   config.
5. Downloads the pre-trained register classifiers (~6 GB) to
   `~/.vedix/models/`. Skip with `--skip-models` if you only need the SaaS.

## Verify

In any installed agent, run:

```text
/vedix linear regression on synthetic data
```

A setup form should appear. If you see it, the install worked. If you don't,
see [troubleshooting](./getting-started.md#troubleshooting).

## Upgrade

```bash
~/.vedix/repo/scripts/update.sh
```

(Windows: `~/.vedix/repo/scripts/update.ps1`)

## Uninstall

```bash
rm -rf ~/.vedix
```

Then remove the plugin entry from each host's config (the installer prints
exact paths during installation so you can find them later).

## Minimum requirements

- Python 3.11 or newer
- At least one of: Claude Code, Codex CLI, or Gemini CLI on `PATH`
- ~10 GB free disk (6 GB classifiers + ~4 GB for jobs, caches, and corpora)
- A BYOK API key for at least one provider, or a Vedix.ai SaaS account
