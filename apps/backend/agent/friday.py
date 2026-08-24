from __future__ import annotations

import uuid
from typing import Any, Callable, Awaitable

from llm.provider import get_provider
from config import Settings
from tools.registry import TOOL_DEFINITIONS, confirm_action, execute_tool

SYSTEM_PROMPT = """Ты — Пятница (FRIDAY), персональный AI-ассистент женского рода.
Говори о себе в женском роде. Тебя вызывают по имени «Пятница».
Отвечай кратко — ответы озвучиваются голосом.
Ты управляешь этим компьютером: приложения, папки, громкость, яркость, медиа, блокировка,
скриншот, список процессов, буфер обмена. Выключать Windows — только через system_power.
Чтобы полностью закрыть себя — quit_friday.
Язык ответа — язык пользователя (обычно русский)."""

MAX_TOOL_ROUNDS = 5


class FridayAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.history = []

    async def run(
        self,
        user_message: str,
        on_delta: Callable[[str], Awaitable[None]],
        on_tool: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
        on_confirm: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> str:
        self.history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]

        provider = get_provider(self.settings)
        full_response = ""

        for _ in range(MAX_TOOL_ROUNDS):
            round_text = ""
            tool_calls: list[dict[str, Any]] = []

            async for chunk in provider.chat_stream(messages, TOOL_DEFINITIONS):
                if chunk["type"] == "text":
                    round_text += chunk["content"]
                    await on_delta(chunk["content"])
                elif chunk["type"] == "tool_call":
                    tool_calls.append(chunk)

            if not tool_calls:
                full_response = round_text
                self.history.append({"role": "assistant", "content": full_response})
                return full_response

            self.history.append({"role": "assistant", "content": round_text or "[tool call]"})
            messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]

            for tc in tool_calls:
                name = tc["name"]
                args = tc.get("arguments", {})
                action_id = str(uuid.uuid4()) if name in ("system_power", "close_app", "empty_recycle") else None

                if on_tool:
                    await on_tool(name, args)

                result, needs_confirm = await execute_tool(name, args, action_id)
                if needs_confirm and on_confirm and action_id:
                    await on_confirm(action_id, f"Confirm {name} ({args})?")
                    result = f"Confirmation requested for {args.get('action')}."

                tool_msg = f"[Tool {name} result]: {result}"
                self.history.append({"role": "user", "content": tool_msg})
                messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.history]

        return full_response

    def handle_confirmation(self, action_id: str, confirmed: bool) -> str:
        return confirm_action(action_id, confirmed)
