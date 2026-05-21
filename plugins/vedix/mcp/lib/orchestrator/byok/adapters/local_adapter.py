"""Self-hosted adapter — OpenAI-compatible API for vLLM / Ollama / llama.cpp."""
from __future__ import annotations

from ..base import ProviderCapabilities
from .openai_adapter import OpenAIAdapter


class LocalAdapter(OpenAIAdapter):
    name = "local"

    def __init__(
        self,
        api_key: str = "none",
        base_url: str = "http://localhost:8000/v1",
        max_context: int = 8192,
    ):
        super().__init__(api_key=api_key, base_url=base_url)
        self._max_context = max_context

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="local",
            region="self-hosted",
            max_context=self._max_context,
            supports_tools=False,
            supports_streaming=True,
            supports_structured_output=False,
            supports_vision=False,
        )
