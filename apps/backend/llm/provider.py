from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from config import Settings


class LLMProvider(ABC):
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield chunks: {type: 'text', content} or {type: 'tool_call', ...}"""


def get_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider in ("openai", "qwen", "ollama"):
        from llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)
    if settings.llm_provider == "anthropic":
        from llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings)
    if settings.llm_provider == "google":
        from llm.google_provider import GoogleProvider

        return GoogleProvider(settings)
    raise ValueError(f"Unknown provider: {settings.llm_provider}")
