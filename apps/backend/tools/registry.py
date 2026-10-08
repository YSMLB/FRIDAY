from __future__ import annotations

from typing import Any, Callable, Awaitable

from duckduckgo_search import DDGS

from tools.desktop import (
    clipboard_set,
    close_app,
    empty_recycle,
    list_running,
    lock_workstation,
    media_key,
    open_folder,
    set_brightness,
    set_mute,
    take_screenshot,
)
from tools.system import open_app, set_volume, system_power
from tools.weather import get_weather

ToolHandler = Callable[[dict[str, Any]], Awaitable[str] | str]

CONFIRM_TOOLS = {"system_power", "close_app", "empty_recycle"}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on this computer by name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close a running application by process name. Requires confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Open a folder in Explorer. Use downloads, desktop, documents, pictures, music, videos, or a full path.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set system master volume 0-100.",
            "parameters": {
                "type": "object",
                "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 100}},
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_mute",
            "description": "Mute or unmute system audio.",
            "parameters": {
                "type": "object",
                "properties": {"muted": {"type": "boolean"}},
                "required": ["muted"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set display brightness 0-100.",
            "parameters": {
                "type": "object",
                "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 100}},
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "media_key",
            "description": "Send a media key: play_pause, next, previous, stop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["play_pause", "next", "previous", "stop"]}
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_workstation",
            "description": "Lock the Windows session.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture the primary screen to Pictures/FRIDAY.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_running",
            "description": "List notable running processes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_set",
            "description": "Copy text to the clipboard.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "empty_recycle",
            "description": "Empty the Recycle Bin. Requires confirmation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quit_friday",
            "description": "Fully quit the FRIDAY application and stop its background processes.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_power",
            "description": "Shutdown, restart, or sleep the computer. Requires confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["shutdown", "restart", "sleep"]}
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
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
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


def _run_tool(name: str, args: dict[str, Any]) -> str:
    if name == "open_app":
        return open_app(args.get("name", ""))
    if name == "close_app":
        return close_app(args.get("name", ""))
    if name == "open_folder":
        return open_folder(args.get("path", ""))
    if name == "get_weather":
        return ""
    if name == "set_volume":
        return set_volume(int(args.get("level", 50)))
    if name == "set_mute":
        return set_mute(bool(args.get("muted")))
    if name == "set_brightness":
        return set_brightness(int(args.get("level", 50)))
    if name == "media_key":
        return media_key(str(args.get("action") or "play_pause"))
    if name == "lock_workstation":
        return lock_workstation()
    if name == "take_screenshot":
        return take_screenshot()
    if name == "list_running":
        return list_running()
    if name == "clipboard_set":
        return clipboard_set(str(args.get("text") or ""))
    if name == "empty_recycle":
        return empty_recycle()
    if name == "quit_friday":
        return "Останавливаю FRIDAY."
    if name == "web_search":
        return ""
    if name == "system_power":
        return system_power(args.get("action", ""))
    return f"Unknown tool: {name}"


async def execute_tool(name: str, args: dict[str, Any], action_id: str | None = None) -> tuple[str, bool]:
    if name == "get_weather":
        return await get_weather(str(args.get("city") or "Оренбург")), False
    if name == "web_search":
        return await web_search(args), False
    if name in CONFIRM_TOOLS:
        if action_id:
            PENDING_CONFIRMATIONS[action_id] = {"name": name, "args": args}
            return f"Awaiting confirmation for {name}.", True
        return _run_tool(name, args), False
    return _run_tool(name, args), False


def confirm_action(action_id: str, confirmed: bool) -> str:
    pending = PENDING_CONFIRMATIONS.pop(action_id, None)
    if not pending:
        return "No pending action found."
    if not confirmed:
        return "Action cancelled by user."
    return _run_tool(pending["name"], pending.get("args") or {})
