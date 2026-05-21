"""ProviderAdapter protocol + BYOK request/response dataclasses.

A provider adapter is a thin async wrapper that normalizes one provider's
chat-completion API behind a uniform ``chat`` / ``stream`` / ``count_tokens``
interface. Adapters are registered with a ``ProviderRouter`` which dispatches
a request to the first adapter in its fallback chain whose capabilities can
serve the request, retrying on rate-limit / 5xx / context-overflow.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterable, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class ChatRequest:
    messages: list[Message]
    model: str
    max_tokens: int = 1024
    temperature: float = 0.7
    stop_sequences: list[str] = field(default_factory=list)
    tools: list[dict] | None = None
    response_schema: dict | None = None


@dataclass
class ChatResponse:
    content: str
    model: str
    finish_reason: str
    input_tokens: int
    output_tokens: int
    tool_calls: list[dict] | None = None
    raw: dict | None = None  # provider-native payload for debugging


@dataclass
class ProviderCapabilities:
    name: str
    region: Literal["global", "ru", "cn", "eu", "self-hosted"]
    max_context: int
    supports_tools: bool
    supports_streaming: bool
    supports_structured_output: bool
    supports_vision: bool = False


@runtime_checkable
class ProviderAdapter(Protocol):
    @property
    def name(self) -> str: ...
    def capabilities(self) -> ProviderCapabilities: ...
    async def chat(self, req: ChatRequest) -> ChatResponse: ...
    async def stream(self, req: ChatRequest) -> AsyncIterator[str]: ...
    def count_tokens(self, messages: Iterable[Message]) -> int: ...
