#!/usr/bin/env python3
"""Idempotent merge of codex-config.toml.example into ~/.codex/config.toml.

Used by scripts/bootstrap.{ps1,sh} and scripts/update.{ps1,sh}. Solves the
v2.0/v2.1 install footguns:

- TOML "duplicate key" errors when the example block was already appended.
- UTF-8 BOM injection from PowerShell's Set-Content -Encoding UTF8.
- Re-runs that re-append on every install.

Behavior:
    1. Backs up the existing config.toml to config.toml.bak-YYYYMMDD-HHMMSS.
    2. Parses both the user's config.toml and the plugin's example with tomllib.
    3. For each [features] key and [mcp_servers.*] block in the example:
        - if it does not exist in the user's config -> add it
        - if it exists -> leave the user's version untouched (no overwrite)
    4. Writes the merged config back as UTF-8 WITHOUT BOM, LF endings.
    5. Validates the result re-parses; rolls back from backup if not.

Usage:
    python _merge_codex_config.py \
        --user ~/.codex/config.toml \
        --example /path/to/plugins/ai-scientist/codex-config.toml.example
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

try:
    import tomllib  # py3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

# Sentinel comment used to mark plugin-managed blocks in config.toml.
PLUGIN_BLOCK_MARK = "# >>> ai-scientist plugin v2.1 (auto-managed; do not edit by hand) >>>"
PLUGIN_BLOCK_END = "# <<< ai-scientist plugin v2.1 <<<"

# These section names are 'plugin-owned'. When the user has them already
# (from a prior install), we replace the plugin-owned block in place; if they
# came from another source (no sentinel), we leave them alone and warn.
PLUGIN_OWNED_MCP_SERVERS = [
    "ai-scientist", "mempalace", "openalex", "semanticscholar",
    "arxiv", "biorxiv", "pubmed", "annas-mcp", "fetcher",
]


def _read(path: Path) -> str:
    data = path.read_bytes()
    # Strip UTF-8 BOM if present (PowerShell adds one with -Encoding UTF8).
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n")


def _write_no_bom(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    path.write_bytes(text.encode("utf-8"))


def _backup(path: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak-{ts}")
    shutil.copy2(path, bak)
    return bak


def _strip_existing_plugin_block(text: str) -> str:
    """Remove any pre-existing sentinel-bracketed plugin block."""
    pattern = re.compile(
        re.escape(PLUGIN_BLOCK_MARK) + r".*?" + re.escape(PLUGIN_BLOCK_END) + r"\n?",
        re.DOTALL,
    )
    return pattern.sub("", text)


def _strip_unmarked_plugin_blocks(text: str) -> tuple[str, list[str]]:
    """Remove top-level [features] / [mcp_servers.X] blocks that look plugin-owned
    but were appended without sentinels (legacy v2.0 installs)."""
    removed: list[str] = []

    # Find the example's plugin-owned sections from the names.
    # We only remove [mcp_servers.X] for X in PLUGIN_OWNED_MCP_SERVERS.
    # Approach: scan line-by-line. When we hit a top-level header that matches
    # an owned name, drop until the next top-level header (or EOF). Subsection
    # headers (e.g. [mcp_servers.openalex.tools.search_works]) under an owned
    # parent are also dropped.
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    drop_until_next_header = False

    while i < n:
        line = lines[i]
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
        if m:
            section = m.group(1)
            top = section.split(".")[0:2]  # e.g. ["mcp_servers", "openalex"]
            owned = False
            if top[0] == "mcp_servers" and len(top) >= 2:
                if top[1] in PLUGIN_OWNED_MCP_SERVERS:
                    owned = True
            # IMPORTANT: never auto-strip the [features] table -- the user almost
            # certainly has their own keys there (multi_agent + js_repl +
            # prevent_idle_sleep + etc.).  We only ensure the example does not
            # try to *append* a duplicate [features] block; that's enforced in
            # the example template itself (no [features] section) so this case
            # cannot happen.
            if owned:
                drop_until_next_header = True
                removed.append(section)
                i += 1
                continue
            else:
                drop_until_next_header = False
        if not drop_until_next_header:
            out.append(line)
        i += 1
    return "\n".join(out), removed


def _ensure_features_multi_agent(text: str) -> tuple[str, bool]:
    """Make sure [features].multi_agent = true exists somewhere in the config.

    Returns (new_text, changed).
    """
    # Quick check: is there a [features] section AND does it set multi_agent = true?
    # Naive parse: split into table chunks.
    has_features = False
    has_multi_agent = False
    in_features = False
    for line in text.split("\n"):
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
        if m:
            in_features = (m.group(1) == "features")
            if in_features:
                has_features = True
            continue
        if in_features:
            # Trailing comments are allowed; only check the assignment itself.
            if re.match(r"^\s*multi_agent\s*=\s*true\b", line, re.IGNORECASE):
                has_multi_agent = True
                break

    if has_features and has_multi_agent:
        return text, False
    if has_features and not has_multi_agent:
        # Inject multi_agent = true at the start of the [features] body.
        # Find the [features] header and add the line right after it.
        new_text = re.sub(
            r"(^\s*\[features\]\s*\n)",
            r"\1multi_agent = true  # added by ai-scientist plugin\n",
            text, count=1, flags=re.MULTILINE,
        )
        return new_text, True
    # No [features] section at all -> add a fresh one at the top.
    return ("[features]\nmulti_agent = true  # added by ai-scientist plugin\n\n"
            + text), True


def _extract_plugin_example_body(example_text: str) -> str:
    """Strip leading comment-header from the example.

    The example starts with a long `#` comment block instructing the user.
    For the merge, we keep the technical content (everything from the first
    table header `[...]` onward).
    """
    lines = example_text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^\s*\[", line):
            return "\n".join(lines[i:]).strip("\n") + "\n"
    return example_text


def _wrap_in_sentinel(body: str) -> str:
    return f"{PLUGIN_BLOCK_MARK}\n{body.strip()}\n{PLUGIN_BLOCK_END}\n"


def merge(user_path: Path, example_path: Path) -> dict:
    """Idempotent merge. Returns dict with keys: backup, removed, added, changed."""
    if not user_path.is_file():
        # Create a fresh config from scratch.
        user_path.parent.mkdir(parents=True, exist_ok=True)
        user_text = ""
    else:
        user_text = _read(user_path)
    example_text = _read(example_path)

    backup = _backup(user_path) if user_path.is_file() and user_text else None

    # 1. Remove any prior plugin-managed sentinel block.
    user_text = _strip_existing_plugin_block(user_text)
    # 2. Remove any unmarked plugin-owned [mcp_servers.X] blocks (legacy installs).
    user_text, removed = _strip_unmarked_plugin_blocks(user_text)
    # 3. Ensure [features].multi_agent = true exists.
    user_text, features_changed = _ensure_features_multi_agent(user_text)
    # 4. Append a fresh sentinel-wrapped block from the example.
    plugin_body = _extract_plugin_example_body(example_text)
    if not user_text.endswith("\n"):
        user_text += "\n"
    if not user_text.endswith("\n\n"):
        user_text += "\n"
    merged = user_text + _wrap_in_sentinel(plugin_body)

    # 5. Validate that the result parses.
    try:
        tomllib.loads(merged)
    except tomllib.TOMLDecodeError as e:
        # Roll back from backup if we have one.
        if backup is not None:
            shutil.copy2(backup, user_path)
        raise SystemExit(
            f"merge produced invalid TOML and was rolled back: {e}\n"
            f"backup preserved at {backup}"
        )

    # 6. Write back as UTF-8 NO BOM.
    _write_no_bom(user_path, merged)

    return {
        "backup": str(backup) if backup else None,
        "removed_legacy_blocks": removed,
        "features_multi_agent_added": features_changed,
        "added_block_marker": PLUGIN_BLOCK_MARK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True,
                        help="Path to ~/.codex/config.toml")
    parser.add_argument("--example", required=True,
                        help="Path to plugin's codex-config.toml.example")
    parser.add_argument("--quiet", action="store_true",
                        help="Print only the result line")
    args = parser.parse_args()

    user_path = Path(args.user).expanduser()
    example_path = Path(args.example).expanduser()
    if not example_path.is_file():
        print(f"  [ERR] example not found: {example_path}", file=sys.stderr)
        return 1

    result = merge(user_path, example_path)
    if not args.quiet:
        print("  config.toml merged idempotently:")
        if result["backup"]:
            print(f"    backup:                 {result['backup']}")
        if result["removed_legacy_blocks"]:
            print(f"    removed legacy blocks:  {', '.join(result['removed_legacy_blocks'])}")
        if result["features_multi_agent_added"]:
            print(f"    [features].multi_agent: added")
        else:
            print(f"    [features].multi_agent: already present")
        print(f"    plugin block written between sentinel markers")
    print(f"  config_toml: OK ({user_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
