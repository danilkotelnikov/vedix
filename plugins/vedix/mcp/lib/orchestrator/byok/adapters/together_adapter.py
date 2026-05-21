"""Together.ai adapter — OpenAI-compatible inference for open models."""
from __future__ import annotations

from ..base import ProviderCapabilities
from .openai_adapter import OpenAIAdapter


class TogetherAdapter(OpenAIAdapter):
    name = "together"

    def __init__(self, api_key: str):
        super().__init__(api_key=api_key, base_url="https://api.together.xyz/v1")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="together",
            region="global",
            max_context=32_768,
            supports_tools=False,
            supports_streaming=True,
            supports_structured_output=False,
            supports_vision=False,
        )
