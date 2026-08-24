from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types

from config import Settings
from llm.provider import LLMProvider

# Gemini function Schema rejects many JSON Schema keywords (e.g. minimum/maximum).
_GEMINI_SCHEMA_KEYS = frozenset(
    {
        "type",
        "format",
        "description",
        "nullable",
        "enum",
        "items",
        "properties",
        "required",
        "anyOf",
    }
)


def _sanitize_gemini_schema(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return schema
    cleaned: dict[str, Any] = {}
    for key, value in schema.items():
        if key not in _GEMINI_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {k: _sanitize_gemini_schema(v) for k, v in value.items()}
        elif key == "items":
            cleaned[key] = _sanitize_gemini_schema(value)
        elif key == "anyOf" and isinstance(value, list):
            cleaned[key] = [_sanitize_gemini_schema(v) for v in value]
        else:
            cleaned[key] = value
    return cleaned


class GoogleProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_name = settings.llm_model or "gemini-2.0-flash"
        self._client: genai.Client | None = None

    def _client_or_raise(self) -> genai.Client:
        if not self.settings.google_api_key:
            raise ValueError("Google API key not configured. Add it in Settings.")
        if self._client is None:
            # New google-genai SDK sends AQ./AIza keys via x-goog-api-key (not Bearer).
            self._client = genai.Client(api_key=self.settings.google_api_key)
        return self._client

    def _build_tools(self, tools: list[dict[str, Any]] | None) -> list[types.Tool] | None:
        if not tools:
            return None
        declarations: list[types.FunctionDeclaration] = []
        for t in tools:
            fn = t["function"]
            declarations.append(
                types.FunctionDeclaration(
                    name=fn["name"],
                    description=fn.get("description", ""),
                    parameters_json_schema=_sanitize_gemini_schema(fn.get("parameters", {})),
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _contents_from_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str | None, list[types.Content]]:
        system: str | None = None
        contents: list[types.Content] = []
        for msg in messages:
            role = msg["role"]
            text = msg["content"]
            if role == "system":
                system = text
            elif role == "user":
                contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=text)])
                )
            elif role == "assistant":
                contents.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=text)])
                )
        return system, contents

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._client_or_raise()
        system, contents = self._contents_from_messages(messages)
        gemini_tools = self._build_tools(tools)
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=gemini_tools,
            # We execute tools ourselves in FridayAgent; disable SDK auto-calling.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        try:
            stream = await client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            msg = str(exc)
            if "401" in msg or "UNAUTHENTICATED" in msg or "ACCESS_TOKEN_TYPE" in msg:
                raise ValueError(
                    "Google API key rejected (401). Create a new key at "
                    "https://aistudio.google.com/apikey and paste it in Settings, "
                    "or switch provider to OpenAI/Anthropic."
                ) from exc
            raise

        async for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield {"type": "text", "content": text}

            function_calls = getattr(chunk, "function_calls", None) or []
            for fc in function_calls:
                args = dict(fc.args) if getattr(fc, "args", None) else {}
                yield {
                    "type": "tool_call",
                    "id": fc.name,
                    "name": fc.name,
                    "arguments": args,
                }
