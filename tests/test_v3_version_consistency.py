# tests/test_v3_version_consistency.py
"""Verify B1 Task 7: every declared version string is 3.0.x.

`json.loads()` returns `Any` at the runtime/JSON-text boundary; per-line
`# pyright: ignore[reportAny]` directives are the idiomatic way to acknowledge
that without polluting test code with TypedDict scaffolding.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_plugin_manifest_is_v3() -> None:
    manifest = json.loads(  # pyright: ignore[reportAny]
        (ROOT / "plugins" / "vedix" / ".claude-plugin" / "plugin.json")
        .read_text(encoding="utf-8")
    )
    assert manifest["version"].startswith("3.0"), (  # pyright: ignore[reportAny]
        "plugin.json version must start with 3.0"
    )


def test_gemini_extension_is_v3() -> None:
    manifest = json.loads(  # pyright: ignore[reportAny]
        (ROOT / "gemini-extension.json").read_text(encoding="utf-8")
    )
    assert manifest["version"].startswith("3.0"), (  # pyright: ignore[reportAny]
        "gemini-extension.json version must start with 3.0"
    )


def test_mcp_server_serverinfo_is_v3() -> None:
    server_py = (
        ROOT / "plugins" / "vedix" / "mcp" / "server.py"
    ).read_text(encoding="utf-8")
    assert re.search(r'"version"\s*:\s*"3\.0', server_py) or re.search(
        r"'version'\s*:\s*'3\.0", server_py
    ), "server.py must contain a 3.0.x version literal in serverInfo"
