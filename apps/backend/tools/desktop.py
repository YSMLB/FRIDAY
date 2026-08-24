from __future__ import annotations

import ctypes
import os
import subprocess
from pathlib import Path

import psutil

PROTECTED = {
    "csrss.exe",
    "wininit.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "svchost.exe",
    "system",
}


def lock_workstation() -> str:
    if os.name != "nt":
        return "Lock is only supported on Windows."
    ctypes.windll.user32.LockWorkStation()
    return "Workstation locked."


def take_screenshot() -> str:
    if os.name != "nt":
        return "Screenshot is only supported on Windows."
    pictures = Path.home() / "Pictures" / "FRIDAY"
    pictures.mkdir(parents=True, exist_ok=True)
    out = pictures / "capture.png"
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; "
        "$g=[System.Drawing.Graphics]::FromImage($bmp); "
        "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); "
        f"$bmp.Save('{str(out).replace(chr(39), '')}'); "
        "$g.Dispose(); $bmp.Dispose();"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)
    if out.exists():
        return f"Screenshot saved to {out}"
    return "Screenshot failed."


def set_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))
    if os.name != "nt":
        return "Brightness is only supported on Windows."
    cmd = (
        f"$m=Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods "
        f"-ErrorAction SilentlyContinue; "
        f"if($m){{ $m | ForEach-Object {{ $_.WmiSetBrightness(1,{level}) }} }}"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    if r.returncode != 0:
        return f"Failed to set brightness: {r.stderr.strip() or r.stdout.strip()}"
    return f"Brightness set to {level}%."


def media_key(action: str) -> str:
    if os.name != "nt":
        return "Media keys are only supported on Windows."
    keys = {
        "play_pause": 0xB3,
        "next": 0xB0,
        "previous": 0xB1,
        "stop": 0xB2,
    }
    vk = keys.get((action or "").strip().lower())
    if vk is None:
        return f"Unknown media action: {action}"
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)
    return f"Media: {action}."


def set_mute(muted: bool) -> str:
    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(1 if muted else 0, None)
        return "Sound muted." if muted else "Sound unmuted."
    except Exception as exc:
        return f"Mute failed: {exc}"


def open_folder(path: str) -> str:
    target = Path(path).expanduser()
    if not target.exists():
        known = {
            "downloads": Path.home() / "Downloads",
            "desktop": Path.home() / "Desktop",
            "documents": Path.home() / "Documents",
            "pictures": Path.home() / "Pictures",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
        }
        target = known.get(path.strip().lower(), target)
    if not target.exists():
        return f"Path not found: {path}"
    os.startfile(str(target))  # type: ignore[attr-defined]
    return f"Opened {target}"


def list_running(limit: int = 12) -> str:
    rows: list[tuple[float, str]] = []
    for p in psutil.process_iter(["name", "cpu_percent"]):
        name = (p.info.get("name") or "").strip()
        if not name:
            continue
        rows.append((float(p.info.get("cpu_percent") or 0), name))
    rows.sort(reverse=True)
    seen: list[str] = []
    for _, name in rows:
        if name.lower() not in {x.lower() for x in seen}:
            seen.append(name)
        if len(seen) >= limit:
            break
    return "Running: " + ", ".join(seen) if seen else "No processes listed."


def close_app(name: str) -> str:
    key = (name or "").strip().lower()
    if not key:
        return "No application name provided."
    killed = 0
    for p in psutil.process_iter(["name"]):
        pname = (p.info.get("name") or "").lower()
        if pname in PROTECTED:
            continue
        if key in pname or pname.startswith(key):
            try:
                p.terminate()
                killed += 1
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
    if killed:
        return f"Closed {killed} process(es) matching {name}."
    return f"No running process matched {name}."


def empty_recycle() -> str:
    if os.name != "nt":
        return "Recycle bin is only supported on Windows."
    SHERB_NOCONFIRMATION = 0x00000001
    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SHERB_NOCONFIRMATION)
    return "Recycle bin emptied."


def clipboard_set(text: str) -> str:
    if os.name != "nt":
        return "Clipboard is only supported on Windows."
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
        input=text,
        text=True,
        check=False,
    )
    return "Copied to clipboard."
