"""Moonshot Kimi adapter — OpenAI-compatible Chinese-direct provider."""
from __future__ import annotations

from ..base import ProviderCapabilities
from .openai_adapter import OpenAIAdapter


class MoonshotAdapter(OpenAIAdapter):
    name = "moonshot"

    def __init__(self, api_key: str):
        super().__init__(api_key=api_key, base_url="https://api.moonshot.cn/v1")

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="moonshot",
            region="cn",
            max_context=128_000,
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=False,
            supports_vision=False,
        )
