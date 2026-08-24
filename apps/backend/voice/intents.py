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

    for matcher in (
        _match_quit,
        _match_lock,
        _match_screenshot,
        _match_media,
        _match_mute,
        _match_volume,
        _match_brightness,
        _match_folder,
        _match_close_app,
        _match_weather,
        _match_open_app,
        _match_power,
    ):
        hit = matcher(low)
        if hit:
            return hit
    return None


def _match_quit(low: str) -> dict[str, Any] | None:
    if re.search(
        r"(выключись|выключи себя|закрой(ся)?|останови(сь)?|заверши работу|"
        r"выключи пятниц|закрой пятниц|quit|exit friday|shutdown friday)",
        low,
    ):
        if re.search(r"(компьютер|пк|windows|систему|ноутбук)", low):
            return None
        return {"name": "quit_friday", "args": {}}
    return None


def _match_lock(low: str) -> dict[str, Any] | None:
    if re.search(r"(заблокируй|блокировк|lock (pc|computer|workstation)|lock screen)", low):
        return {"name": "lock_workstation", "args": {}}
    return None


def _match_screenshot(low: str) -> dict[str, Any] | None:
    if re.search(r"(скриншот|снимок экрана|screenshot)", low):
        return {"name": "take_screenshot", "args": {}}
    return None


def _match_media(low: str) -> dict[str, Any] | None:
    if re.search(r"(пауза|продолж|play|pause|стоп музык)", low) and re.search(
        r"(музык|трек|песн|spotify|media|воспроиз)", low
    ):
        return {"name": "media_key", "args": {"action": "play_pause"}}
    if re.search(r"(следующ(ий|ая)|next track|next song)", low):
        return {"name": "media_key", "args": {"action": "next"}}
    if re.search(r"(предыдущ|previous track)", low):
        return {"name": "media_key", "args": {"action": "previous"}}
    return None


def _match_mute(low: str) -> dict[str, Any] | None:
    if re.search(r"(выключи звук|без звука|mute|заглуши)", low):
        return {"name": "set_mute", "args": {"muted": True}}
    if re.search(r"(включи звук|unmute|со звуком)", low):
        return {"name": "set_mute", "args": {"muted": False}}
    return None


def _match_volume(low: str) -> dict[str, Any] | None:
    if not re.search(r"(громкост|звук|volume)", low):
        return None
    m = re.search(r"(\d{1,3})\s*%?", low)
    if m:
        return {"name": "set_volume", "args": {"level": int(m.group(1))}}
    if re.search(r"(максимум|на полную|full)", low):
        return {"name": "set_volume", "args": {"level": 100}}
    if re.search(r"(тихо|минимум)", low):
        return {"name": "set_volume", "args": {"level": 10}}
    return None


def _match_brightness(low: str) -> dict[str, Any] | None:
    if not re.search(r"(яркост|brightness)", low):
        return None
    m = re.search(r"(\d{1,3})", low)
    if m:
        return {"name": "set_brightness", "args": {"level": int(m.group(1))}}
    return None


def _match_folder(low: str) -> dict[str, Any] | None:
    if not re.search(r"(открой|открыть|open)", low):
        return None
    folders = {
        "загрузк": "downloads",
        "downloads": "downloads",
        "рабоч(ий|его) стол": "desktop",
        "desktop": "desktop",
        "документ": "documents",
        "pictures": "pictures",
        "изображен": "pictures",
        "музык": "music",
        "видео": "videos",
    }
    for phrase, alias in folders.items():
        if re.search(phrase, low):
            return {"name": "open_folder", "args": {"path": alias}}
    return None


def _match_close_app(low: str) -> dict[str, Any] | None:
    if not re.search(r"(закрой|закрыть|выключи|убей процесс|close|kill)", low):
        return None
    if "пятниц" in low or "friday" in low:
        return None
    for phrase, alias in sorted(APP_PHRASES, key=lambda x: len(x[0]), reverse=True):
        if phrase in low:
            return {"name": "close_app", "args": {"name": alias}}
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


def _match_power(low: str) -> dict[str, Any] | None:
    if re.search(r"(выключи компьютер|выключи пк|shutdown pc|shut down the computer)", low):
        return {"name": "system_power", "args": {"action": "shutdown"}}
    if re.search(r"(перезагруз|restart (pc|computer))", low):
        return {"name": "system_power", "args": {"action": "restart"}}
    if re.search(r"(спящий|sleep the (pc|computer))", low):
        return {"name": "system_power", "args": {"action": "sleep"}}
    return None
