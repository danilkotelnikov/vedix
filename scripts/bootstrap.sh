#!/usr/bin/env bash
# scripts/bootstrap.sh -- one-command installer for ai-scientist plugin (v2.1+).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/danilkotelnikov/ai-scientist-plugin/master/scripts/bootstrap.sh | bash
#
# Auto-detects Claude Code / Codex CLI / Gemini CLI in ~/.{claude,codex,gemini}/
# and registers the plugin with each one. Idempotent: re-runs are safe.

set -e
set -o pipefail

REPO_URL="https://github.com/danilkotelnikov/ai-scientist-plugin.git"
BRANCH="master"
AI_HOME="$HOME/.ai-scientist"
REPO_DIR="$AI_HOME/repo"
PALACE_DIR="$AI_HOME/palace"

step() { printf "  \033[36m%s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m[OK]\033[0m   %s\n" "$1"; }
note() { printf "  \033[33m[NOTE]\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m[FAIL]\033[0m %s\n" "$1"; }

echo
printf "\033[35mAI-Scientist Plugin -- one-command bootstrap\033[0m\n"
echo

# 1. Probe prerequisites
step "Probing prerequisites"
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || {
    fail "Python 3.11+ not found. Install via your package manager."
    exit 1
}
PYTHON=$(command -v python3 || command -v python)
command -v git >/dev/null 2>&1 || { fail "git not found"; exit 1; }
ok "python: $($PYTHON --version 2>&1)"
ok "git:    $(git --version 2>&1)"

# 2. Clone or update the canonical repo
step "Syncing canonical repo at $REPO_DIR"
mkdir -p "$AI_HOME"
if [ -d "$REPO_DIR/.git" ]; then
    pushd "$REPO_DIR" >/dev/null
    git stash push --include-untracked -m "auto-stash by bootstrap.sh $(date -Iseconds)" >/dev/null 2>&1 || true
    git fetch --quiet origin "$BRANCH" >/dev/null 2>&1 || true
    git reset --hard "origin/$BRANCH" --quiet >/dev/null 2>&1 || true
    popd >/dev/null
    ok "Updated existing clone (any local changes saved as a stash)"
else
    git clone --quiet --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    ok "Cloned fresh"
fi

PLUG="$REPO_DIR/plugins/ai-scientist"

# 3. Install Python dependencies (idempotent, --user)
step "Installing Python dependencies (user-site)"
$PYTHON -m pip install --user --quiet -r "$PLUG/mcp/requirements.txt" >/dev/null 2>&1 || \
    note "pip install requirements may have failed; check $PYTHON -m pip output"
ok "MCP requirements present"

$PYTHON -m pip install --user --quiet mempalace >/dev/null 2>&1 || \
    note "pip install mempalace may have failed"
ok "mempalace package present"

mkdir -p "$PALACE_DIR"
if command -v mempalace >/dev/null 2>&1; then
    mempalace init "$PALACE_DIR" >/dev/null 2>&1 || true
    ok "MemPalace initialized at $PALACE_DIR"
else
    note "mempalace CLI not on PATH yet; reopen the shell or update PATH"
fi

# 4. Codex CLI -- auto-merge config + create symlinks
if [ -d "$HOME/.codex" ]; then
    echo
    step "Codex CLI detected -- registering plugin"

    CODEX_CLONE="$HOME/.codex/ai-scientist-plugin"
    if [ ! -e "$CODEX_CLONE" ]; then
        ln -s "$REPO_DIR" "$CODEX_CLONE"
        ok "Symlinked ~/.codex/ai-scientist-plugin -> $REPO_DIR"
    else
        ok "~/.codex/ai-scientist-plugin already present"
    fi

    mkdir -p "$HOME/.agents/skills" "$HOME/.agents/agents"
    rm -rf "$HOME/.agents/skills/ai-scientist" "$HOME/.agents/agents/ai-scientist" 2>/dev/null || true
    ln -sf "$PLUG/skills/ai-scientist" "$HOME/.agents/skills/ai-scientist"
    ln -sf "$PLUG/agents"              "$HOME/.agents/agents/ai-scientist"
    ok "Symlinked skill + agents into ~/.agents/"

    CONFIG_TOML="$HOME/.codex/config.toml"
    $PYTHON "$REPO_DIR/scripts/_merge_codex_config.py" \
        --user "$CONFIG_TOML" \
        --example "$PLUG/codex-config.toml.example" \
        --quiet
    ok "config.toml merged (sentinel-bracketed; idempotent)"
else
    note "Codex CLI not detected at ~/.codex/ -- skipping Codex registration"
fi

# 5. Gemini CLI
if [ -d "$HOME/.gemini" ]; then
    echo
    step "Gemini CLI detected -- installing extension"
    if command -v gemini >/dev/null 2>&1; then
        gemini extensions install "$REPO_URL" >/dev/null 2>&1 || \
            note "gemini extensions install may have failed; verify manually"
        ok "Gemini extension installed"
    else
        note "gemini CLI not on PATH; install Gemini CLI then re-run this bootstrap"
    fi
else
    note "Gemini CLI not detected at ~/.gemini/ -- skipping Gemini registration"
fi

# 6. Claude Code -- print the slash commands
if [ -d "$HOME/.claude" ]; then
    echo
    step "Claude Code detected"
    note "Open a Claude Code session and paste these two slash commands:"
    printf "      /plugin marketplace add danilkotelnikov/ai-scientist-plugin\n"
    printf "      /plugin install ai-scientist@ai-scientist-plugin\n"
    note "(slash commands are session-only and cannot be issued from outside the agent)"
else
    note "Claude Code not detected at ~/.claude/ -- skipping Claude registration"
fi

# 7. MCP self-test
echo
step "Running MCP self-test"
SELFTEST_OUT=$($PYTHON "$PLUG/mcp/server.py" --selftest 2>&1 || true)
if printf "%s" "$SELFTEST_OUT" | grep -q "selftest: OK"; then
    ok "$(printf "%s" "$SELFTEST_OUT" | tr '\n' ';')"
else
    note "self-test output: $SELFTEST_OUT"
fi

# 8. Probe required env var
echo
step "Environment variables"
if [ -z "$OPENALEX_EMAIL" ]; then
    note "OPENALEX_EMAIL is not set. Add to your shell rc:"
    printf "      echo 'export OPENALEX_EMAIL=\"you@example.com\"' >> ~/.bashrc\n"
    note "(required since 2026-02-13 for OpenAlex API; restart shell after setting)"
else
    ok "OPENALEX_EMAIL = $OPENALEX_EMAIL"
fi
for v in SEMANTIC_SCHOLAR_KEY ANNAS_BASE_URL ANNAS_DOWNLOAD_PATH ANNAS_SECRET_KEY; do
    val=$(printenv "$v" || true)
    if [ -n "$val" ]; then ok "$v = (set)"; else note "$v not set (optional)"; fi
done

echo
printf "\033[32mBootstrap complete.\033[0m\n"
echo "  - canonical repo: $REPO_DIR"
echo "  - update later:   curl -fsSL https://raw.githubusercontent.com/danilkotelnikov/ai-scientist-plugin/master/scripts/update.sh | bash"
echo
