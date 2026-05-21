"""Long-lived stdio MCP subprocess pool (Block 8 Task 4).

The SaaS runs one process per MCP per worker; the plugin / web UI / IDE
plugins talk to the SaaS, and the SaaS funnels JSON-RPC line-delimited
messages over the subprocess's stdin/stdout. Per-MCP locks serialise
concurrent calls so we don't interleave two requests' bytes on stdin.

Hosted MCP fleet (every tier — including Free — sees all 9):

* ``vedix`` — the plugin's own MCP (publisher engine, locale, etc.)
* ``mempalace`` — federated memory palace
* ``openalex`` — alex-mcp
* ``semanticscholar``
* ``arxiv``
* ``biorxiv``
* ``pubmed``
* ``annas-mcp``
* ``fetcher`` — generic web fetcher

The pool is dependency-injectable: tests swap in a ``DummyMCPPool``
without ever spawning an npx process.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any


MCP_COMMANDS: dict[str, list[str]] = {
    "vedix": ["python", "plugins/vedix/mcp/server.py", "--mode", "stdio"],
    "mempalace": ["mempalace-mcp"],
    "openalex": [
        "uvx",
        "--from",
        "git+https://github.com/drAbreu/alex-mcp.git@4.1.0",
        "alex-mcp",
    ],
    "semanticscholar": [
        "python",
        os.path.expanduser(
            "~/.vedix/external/semanticscholar-MCP-Server/semantic_scholar_server.py"
        ),
    ],
    "arxiv": ["uvx", "arxiv-mcp-server"],
    "biorxiv": [
        "python",
        os.path.expanduser("~/.vedix/external/bioRxiv-MCP-Server/biorxiv_server.py"),
    ],
    "pubmed": ["npx", "-y", "pubmed-mcp"],
    "annas-mcp": ["npx", "-y", "annas-mcp", "mcp"],
    "fetcher": ["npx", "-y", "fetcher-mcp"],
}


@dataclass
class MCPSubprocess:
    name: str
    proc: Any  # asyncio.subprocess.Process
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class MCPPool:
    """Manages stdio subprocesses for every hosted MCP."""

    def __init__(self) -> None:
        self._procs: dict[str, MCPSubprocess] = {}
        self._startup_lock = asyncio.Lock()

    async def ensure(self, name: str) -> MCPSubprocess:
        if name in self._procs:
            return self._procs[name]
        async with self._startup_lock:
            if name in self._procs:
                return self._procs[name]
            if name not in MCP_COMMANDS:
                raise KeyError(f"unknown MCP: {name}")
            cmd = MCP_COMMANDS[name]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._procs[name] = MCPSubprocess(name=name, proc=proc)
            return self._procs[name]

    async def call(self, name: str, request: dict[str, Any]) -> dict[str, Any]:
        m = await self.ensure(name)
        if m.proc.stdin is None or m.proc.stdout is None:  # pragma: no cover
            raise RuntimeError(f"MCP {name} has no stdin/stdout")
        async with m.lock:
            data = (json.dumps(request) + "\n").encode("utf-8")
            m.proc.stdin.write(data)
            await m.proc.stdin.drain()
            line = await m.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"MCP {name} returned empty response")
            return json.loads(line.decode("utf-8"))

    async def shutdown(self) -> None:
        for m in list(self._procs.values()):
            try:
                m.proc.terminate()
                await m.proc.wait()
            except ProcessLookupError:  # pragma: no cover
                pass
        self._procs.clear()


_GLOBAL_POOL: MCPPool | None = None


def get_pool() -> MCPPool:
    """Return the process-wide pool (lazy-init)."""
    global _GLOBAL_POOL
    if _GLOBAL_POOL is None:
        _GLOBAL_POOL = MCPPool()
    return _GLOBAL_POOL


def set_pool(pool: MCPPool | None) -> None:
    """Test-time hook to inject a fake pool."""
    global _GLOBAL_POOL
    _GLOBAL_POOL = pool


__all__ = ["MCP_COMMANDS", "MCPPool", "MCPSubprocess", "get_pool", "set_pool"]
