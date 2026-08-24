"""Local intents so small Ollama models don't need tool-calling."""
from __future__ import annotations

import re
from typing import Any

APP_PHRASES: list[tuple[str, str]] = [
    ("google chrome", "chrome"),
    ("гугл хром", "chrome"),
    ("хром", "chrome"),
    ("chrome", "chrome"),
    ("firefox", "firefox"),
    ("файрфокс", "firefox"),
    ("майкрософт эдж", "edge"),
    ("эдж", "edge"),
    ("edge", "edge"),
    ("visual studio code", "vscode"),
    ("vs code", "vscode"),
    ("vscode", "vscode"),
    ("cursor", "cursor"),
    ("курсор", "cursor"),
    ("discord", "discord"),
    ("дискорд", "discord"),
    ("steam", "steam"),
    ("стим", "steam"),
    ("spotify", "spotify"),
    ("спотифай", "spotify"),
    ("калькулятор", "calculator"),
    ("notepad", "notepad"),
    ("блокнот", "notepad"),
    ("проводник", "explorer"),
    ("explorer", "explorer"),
    ("терминал", "terminal"),
    ("powershell", "powershell"),
]


def match_intent(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if len(raw) < 2:
        return None
    low = raw.lower()

    weather = _match_weather(low)
    if weather:
        return weather

    opened = _match_open_app(low)
    if opened:
        return opened

    return None


def _match_weather(low: str) -> dict[str, Any] | None:
    if not re.search(r"(погод|forecast|\bweather\b)", low):
        return None
    city = ""
    m = re.search(
        r"(?:погод\w*\s+(?:в|во|на)\s+|в\s+городе\s+|weather\s+(?:in|for)\s+)(.+)$",
        low,
    )
    if m:
        city = m.group(1)
    else:
        m = re.search(r"(?:в|во)\s+([а-яёa-z\- ]{2,40})$", low)
        if m:
            city = m.group(1)
    city = re.sub(r"[?!.]+$", "", (city or "").strip(" ,.:;"))
    city = re.sub(r"\b(сейчас|сегодня|завтра|пожалуйста)\b", "", city).strip()
    return {"name": "get_weather", "args": {"city": city or "Оренбург"}}


def _match_open_app(low: str) -> dict[str, Any] | None:
    if not re.search(r"(открой|открыть|запусти|запустить|open|launch)", low):
        return None
    for phrase, alias in sorted(APP_PHRASES, key=lambda x: len(x[0]), reverse=True):
        if phrase in low:
            return {"name": "open_app", "args": {"name": alias}}
    return None
