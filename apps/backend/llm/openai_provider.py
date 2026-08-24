from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from config import Settings
from llm.provider import LLMProvider

# Official QwenCloud / DashScope OpenAI-compatible endpoint (intl).
QWEN_DEFAULT_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_DEFAULT_MODEL = "qwen3.7-flash"
OLLAMA_DEFAULT_BASE = "http://127.0.0.1:11434/v1"
OLLAMA_DEFAULT_MODEL = "qwen2.5:3b"


class OpenAIProvider(LLMProvider):
    """OpenAI + OpenAI-compatible endpoints (Ollama, QwenCloud, …)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncOpenAI | None = None
        self._client_key: str | None = None

    def _resolve(self) -> tuple[str, str | None, str]:
        provider = self.settings.llm_provider
        if provider == "ollama":
            base = (self.settings.llm_base_url or OLLAMA_DEFAULT_BASE).strip()
            model = (self.settings.llm_model or OLLAMA_DEFAULT_MODEL).strip()
            # Ollama ignores the key but the OpenAI SDK requires a non-empty value.
            return "ollama", base, model

        if provider == "qwen":
            key = (self.settings.qwen_api_key or self.settings.openai_api_key or "").strip()
            base = (self.settings.llm_base_url or QWEN_DEFAULT_BASE).strip()
            model = (self.settings.llm_model or QWEN_DEFAULT_MODEL).strip()
            if not key:
                raise ValueError(
                    "Qwen API key missing. Set QWEN_API_KEY in the project .env file."
                )
            return key, base, model

        key = (self.settings.openai_api_key or "").strip()
        if not key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env.")
        base = (self.settings.llm_base_url or "").strip() or None
        model = (self.settings.llm_model or "gpt-4o").strip()
        return key, base, model

    @property
    def client(self) -> AsyncOpenAI:
        key, base, _ = self._resolve()
        cache_key = f"{key}|{base or ''}"
        if self._client is None or self._client_key != cache_key:
            kwargs: dict[str, Any] = {"api_key": key}
            if base:
                kwargs["base_url"] = base
            self._client = AsyncOpenAI(**kwargs)
            self._client_key = cache_key
        return self._client

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        _, _, model = self._resolve()
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        # Local Ollama models often choke on tool schemas — chat-only is more reliable.
        if tools and self.settings.llm_provider in ("openai", "qwen"):
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            msg = str(exc)
            if self.settings.llm_provider == "ollama" and (
                "Connection" in msg or "connect" in msg.lower() or "11434" in msg
            ):
                raise ValueError(
                    "Ollama не запущен. Установи Ollama, выполни `ollama pull qwen2.5:3b`, "
                    "затем перезапусти FRIDAY."
                ) from exc
            if "Unpurchased" in msg or "AccessDenied" in msg:
                raise ValueError(
                    "QwenCloud: ключ принят, но модель недоступна. Активируй free quota / billing "
                    "в консоли QwenCloud, затем перезапусти FRIDAY."
                ) from exc
            raise

        tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                yield {"type": "text", "content": delta.content}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls[idx]["arguments"] += tc.function.arguments

            if choice.finish_reason == "tool_calls":
                for tc in tool_calls.values():
                    try:
                        args = json.loads(tc["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    yield {
                        "type": "tool_call",
                        "id": tc["id"],
                        "name": tc["name"],
                        "arguments": args,
                    }
