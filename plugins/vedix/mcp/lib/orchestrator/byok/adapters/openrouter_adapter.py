"""OpenRouter adapter — OpenAI-compatible router for 100+ models.

Adds ``HTTP-Referer`` and ``X-Title`` headers per OpenRouter etiquette.
"""
from __future__ import annotations

from ..base import ProviderCapabilities
from .openai_adapter import OpenAIAdapter


class OpenRouterAdapter(OpenAIAdapter):
    name = "openrouter"

    def __init__(self, api_key: str):
        super().__init__(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        # OpenRouter requires HTTP-Referer + X-Title headers
        self._client._default_headers.update(  # type: ignore[attr-defined]
            {"HTTP-Referer": "https://vedix.ai", "X-Title": "Vedix"}
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="openrouter",
            region="global",
            max_context=128_000,
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=True,
            supports_vision=True,
        )
