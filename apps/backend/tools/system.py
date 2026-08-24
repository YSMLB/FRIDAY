from __future__ import annotations

import os
import subprocess
import time

APP_ALIASES: dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "vscode": "code",
    "code": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "spotify": "spotify",
    "discord": "discord",
    "steam": "steam",
    "стим": "steam",
    "cursor": "cursor",
    "курсор": "cursor",
    "хром": "chrome",
    "гугл хром": "chrome",
    "эдж": "msedge",
    "msedge": "msedge",
}


def open_app(name: str) -> str:
    if not name:
        return "No application name provided."
    key = name.strip().lower()
    cmd = APP_ALIASES.get(key, name.strip())
    try:
        if os.name == "nt":
            subprocess.Popen(["cmd", "/c", "start", "", cmd], shell=False)
        else:
            subprocess.Popen([cmd], shell=True)
        return f"Opened {name}."
    except Exception as exc:
        return f"Failed to open {name}: {exc}"


def set_volume(level: int) -> str:
    level = max(0, min(100, level))
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level}%."
    except Exception as exc:
        return f"Failed to set volume: {exc}"


def system_power(action: str) -> str:
    action = action.lower().strip()
    if os.name != "nt":
        return "Power control is only supported on Windows."
    try:
        if action == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
            return "Shutting down in 5 seconds."
        if action == "restart":
            subprocess.run(["shutdown", "/r", "/t", "5"], check=False)
            return "Restarting in 5 seconds."
        if action == "sleep":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            return "Going to sleep."
        return f"Unknown power action: {action}"
    except Exception as exc:
        return f"Power action failed: {exc}"
