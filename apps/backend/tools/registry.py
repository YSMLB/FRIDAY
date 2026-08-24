from __future__ import annotations

import subprocess
import webbrowser
from typing import Any, Callable, Awaitable

from duckduckgo_search import DDGS

from tools.system import open_app, set_volume, system_power
from tools.weather import get_weather

ToolHandler = Callable[[dict[str, Any]], Awaitable[str] | str]

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the computer by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Application name, e.g. chrome, vscode, notepad, calculator",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set system master volume level from 0 to 100.",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level 0-100",
                        "minimum": 0,
                        "maximum": 100,
                    }
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_power",
            "description": "Control system power: shutdown, restart, or sleep. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["shutdown", "restart", "sleep"],
                        "description": "Power action to perform",
                    }
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web and return brief results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. Use for any weather / forecast question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. Оренбург, Moscow",
                    }
                },
                "required": ["city"],
            },
        },
    },
]

PENDING_CONFIRMATIONS: dict[str, dict[str, Any]] = {}


async def web_search(args: dict[str, Any]) -> str:
    query = args.get("query", "")
    max_results = int(args.get("max_results", 3))
    if not query:
        return "No search query provided."
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   {href}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Search failed: {exc}"


async def execute_tool(name: str, args: dict[str, Any], action_id: str | None = None) -> tuple[str, bool]:
    """Returns (result, needs_confirmation)."""
    if name == "open_app":
        return open_app(args.get("name", "")), False
    if name == "get_weather":
        return await get_weather(str(args.get("city") or "Оренбург")), False
    if name == "set_volume":
        return set_volume(int(args.get("level", 50))), False
    if name == "web_search":
        return await web_search(args), False
    if name == "system_power":
        action = args.get("action", "")
        if action_id:
            PENDING_CONFIRMATIONS[action_id] = {"action": action}
            return f"Awaiting confirmation for {action}.", True
        return system_power(action), False
    return f"Unknown tool: {name}", False


def confirm_action(action_id: str, confirmed: bool) -> str:
    pending = PENDING_CONFIRMATIONS.pop(action_id, None)
    if not pending:
        return "No pending action found."
    if not confirmed:
        return "Action cancelled by user."
    return system_power(pending["action"])
