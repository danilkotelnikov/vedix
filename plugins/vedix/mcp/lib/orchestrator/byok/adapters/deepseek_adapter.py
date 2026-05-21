"""DeepSeek adapter — OpenAI-compatible Chinese-direct provider."""
from __future__ import annotations

from ..base import ProviderCapabilities
from .openai_adapter import OpenAIAdapter


class DeepSeekAdapter(OpenAIAdapter):
    name = "deepseek"

    def __init__(self, api_key: str):
        super().__init__(api_key=api_key, base_url="https://api.deepseek.com/v1")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="deepseek",
            region="cn",
            max_context=64_000,
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=True,
            supports_vision=False,
        )
