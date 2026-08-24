"""Live HUD telemetry: hardware names + CPU/RAM/net/battery."""
from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any

_hw_cache: dict[str, Any] | None = None
_net_prev: tuple[float, int, int] | None = None


def _ps(cmd: str) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


def _hardware() -> dict[str, Any]:
    global _hw_cache
    if _hw_cache:
        return _hw_cache
    cpu = _ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name")
    gpu = _ps(
        "(Get-CimInstance Win32_VideoController | "
        "Where-Object { $_.Name -notmatch 'Microsoft Basic' } | "
        "Select-Object -First 1).Name"
    )
    ram_gb = _ps(
        "[math]::Round(((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory)/1GB,1)"
    )
    disk = _ps("(Get-CimInstance Win32_DiskDrive | Select-Object -First 1).Model")
    board = _ps("(Get-CimInstance Win32_BaseBoard).Product")
    _hw_cache = {
        "cpu": cpu or "CPU",
        "gpu": gpu or "GPU",
        "ram": f"{ram_gb} GB" if ram_gb else "RAM",
        "disk": disk or "DISK",
        "board": board or "MOBO",
    }
    return _hw_cache


def snapshot() -> dict[str, Any]:
    global _net_prev
    cpu_pct = 0.0
    ram_pct = 0.0
    ram_used = ""
    down_kb = 0.0
    up_kb = 0.0
    battery: dict[str, Any] | None = None
    try:
        import psutil

        cpu_pct = float(psutil.cpu_percent(interval=0.15))
        vm = psutil.virtual_memory()
        ram_pct = float(vm.percent)
        ram_used = f"{vm.used / (1024**3):.1f}/{vm.total / (1024**3):.1f} GB"
        n = psutil.net_io_counters()
        now = time.time()
        if _net_prev:
            dt = max(0.2, now - _net_prev[0])
            down_kb = max(0.0, (n.bytes_recv - _net_prev[1]) / dt / 1024)
            up_kb = max(0.0, (n.bytes_sent - _net_prev[2]) / dt / 1024)
        _net_prev = (now, int(n.bytes_recv), int(n.bytes_sent))
        bat = psutil.sensors_battery()
        if bat:
            battery = {"percent": round(bat.percent), "plugged": bool(bat.power_plugged)}
    except Exception:
        pass

    browsers = []
    for name, exe in (("edge", "msedge"), ("chrome", "chrome"), ("firefox", "firefox")):
        if shutil.which(exe):
            browsers.append(name)
    if "edge" not in browsers:
        browsers.insert(0, "edge")

    return {
        "hardware": _hardware(),
        "cpuPercent": round(cpu_pct, 1),
        "ramPercent": round(ram_pct, 1),
        "ramUsed": ram_used,
        "downloadKBs": round(down_kb, 1),
        "uploadKBs": round(up_kb, 1),
        "battery": battery,
        "browsers": browsers,
    }
