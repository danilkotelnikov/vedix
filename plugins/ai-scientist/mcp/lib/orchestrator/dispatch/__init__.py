"""Per-host dispatch backends. detect_host() picks claude_code / codex / gemini."""

from .claude_code import ClaudeCodeDispatcher
from .codex import CodexDispatcher
from .gemini import GeminiDispatcher


def get_dispatcher(host: str):
    """Return the dispatcher class for the given host name."""
    return {
        "claude_code": ClaudeCodeDispatcher,
        "codex": CodexDispatcher,
        "gemini": GeminiDispatcher,
    }[host]


__all__ = ["ClaudeCodeDispatcher", "CodexDispatcher", "GeminiDispatcher", "get_dispatcher"]
