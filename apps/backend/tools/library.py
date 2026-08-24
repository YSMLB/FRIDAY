"""Discover installed apps and Steam games for the desktop library rail."""
from __future__ import annotations

import os
import re
import shutil
import winreg
from pathlib import Path
from typing import Any

KNOWN_APPS: list[tuple[str, str, list[Path]]] = [
    (
        "Cursor",
        "cursor",
        [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor" / "Cursor.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Cursor" / "Cursor.exe",
        ],
    ),
    (
        "VS Code",
        "vscode",
        [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
            Path(os.environ.get("ProgramFiles", "")) / "Microsoft VS Code" / "Code.exe",
        ],
    ),
    (
        "Blender",
        "blender",
        [
            Path(os.environ.get("ProgramFiles", "")) / "Blender Foundation",
        ],
    ),
    ("Chrome", "chrome", [Path(os.environ.get("ProgramFiles", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"]),
    ("Edge", "edge", [Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe"]),
    ("Firefox", "firefox", [Path(os.environ.get("ProgramFiles", "")) / "Mozilla Firefox" / "firefox.exe"]),
    ("Discord", "discord", [Path(os.environ.get("LOCALAPPDATA", "")) / "Discord" / "Update.exe"]),
    ("Steam", "steam", [Path(os.environ.get("ProgramFiles(x86)", "")) / "Steam" / "steam.exe"]),
    ("Spotify", "spotify", [Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe"]),
    ("Notepad", "notepad", []),
    ("Calculator", "calculator", []),
    ("Explorer", "explorer", []),
    ("Terminal", "terminal", []),
    ("PowerShell", "powershell", []),
]

ALWAYS = {"notepad", "calculator", "explorer", "terminal", "powershell", "edge"}


def _exists_any(paths: list[Path]) -> bool:
    for p in paths:
        if not p or str(p) in (".", ""):
            continue
        if p.is_file():
            return True
        if p.is_dir():
            try:
                next(p.rglob("blender.exe"))
                return True
            except (StopIteration, OSError, PermissionError):
                continue
    return False


def _steam_root() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Steam",
    ]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            val, _ = winreg.QueryValueEx(key, "SteamPath")
            if val:
                candidates.insert(0, Path(str(val)))
    except OSError:
        pass
    for c in candidates:
        if c and (c / "steam.exe").exists():
            return c
    return None


def _parse_acf(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, str] = {}
    for key in ("appid", "name", "installdir"):
        m = re.search(rf'"{key}"\s+"([^"]+)"', text, re.I)
        if m:
            out[key.lower()] = m.group(1)
    return out


def list_steam_games(limit: int = 48) -> list[dict[str, Any]]:
    root = _steam_root()
    if not root:
        return []
    games: list[dict[str, Any]] = []
    seen: set[str] = set()
    library_folders = [root / "steamapps"]
    vdf = root / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        raw = vdf.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'"path"\s+"([^"]+)"', raw, re.I):
            library_folders.append(Path(m.group(1).replace("\\\\", "\\")) / "steamapps")
    skip = {"steamworks common redistributables", "steam linux runtime", "steamvr"}
    for apps in library_folders:
        if not apps.is_dir():
            continue
        for acf in apps.glob("appmanifest_*.acf"):
            meta = _parse_acf(acf)
            appid = meta.get("appid")
            name = meta.get("name")
            if not appid or not name or appid in seen:
                continue
            if name.lower() in skip:
                continue
            seen.add(appid)
            games.append(
                {
                    "id": f"steam:{appid}",
                    "name": name,
                    "kind": "game",
                    "launch": f"steam://rungameid/{appid}",
                }
            )
            if len(games) >= limit:
                return sorted(games, key=lambda g: g["name"].lower())
    return sorted(games, key=lambda g: g["name"].lower())


def list_apps() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for label, alias, paths in KNOWN_APPS:
        ok = alias in ALWAYS or shutil.which(alias) or _exists_any(paths)
        if alias == "vscode":
            ok = ok or bool(shutil.which("code"))
        if alias == "blender":
            ok = ok or bool(shutil.which("blender"))
        if ok:
            items.append({"id": f"app:{alias}", "name": label, "kind": "app", "launch": alias})
    return items


def library_snapshot() -> dict[str, Any]:
    apps = list_apps()
    games = list_steam_games()
    tools = [a for a in apps if a["launch"] in {"vscode", "cursor", "blender", "terminal", "powershell", "notepad"}]
    browsers = [a for a in apps if a["launch"] in {"chrome", "edge", "firefox"}]
    create = [a for a in apps if a["launch"] in {"blender", "vscode", "cursor"}]
    return {
        "folders": [
            {"id": "games", "label": "Games", "items": games},
            {"id": "apps", "label": "Apps", "items": apps},
            {"id": "tools", "label": "Tools", "items": tools},
            {"id": "web", "label": "Web", "items": browsers},
            {"id": "create", "label": "Create", "items": create},
        ]
    }
