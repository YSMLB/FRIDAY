from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from config import Settings
from llm.provider import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncAnthropic | None = None

    @property
    def client(self) -> AsyncAnthropic:
        if not self.settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured. Add it in Settings.")
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        system = ""
        conv: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                conv.append({"role": msg["role"], "content": msg["content"]})

        anthropic_tools = None
        if tools:
            anthropic_tools = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]

        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model or "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "messages": conv,
            "system": system,
        }
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "text", "content": text}

            final = await stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use":
                    yield {
                        "type": "tool_call",
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input if isinstance(block.input, dict) else {},
                    }
