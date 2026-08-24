"""Probe input devices and pick the best live microphone."""
from __future__ import annotations

import json
import math
import re
import sys
import time

import numpy as np
import sounddevice as sd


def _safe_rms(x: np.ndarray) -> float:
    x = np.clip(x.astype(np.float64), -1.0, 1.0)
    return float(np.sqrt(np.mean(x * x) + 1e-12))


def _name_flags(name: str) -> dict[str, bool]:
    low = name.lower()
    is_usb = "usb" in low
    is_mic = bool(
        re.search(r"(микрофон|microphone|\bmic\b|mikrofon|mic\s*\(|mic input)", low)
    )
    is_line = bool(re.search(r"(line\s*input|линейн|line in)", low))
    is_stereo_mix = bool(
        re.search(r"(stereo mix|what u hear|смешан|cable|loopback|стерео\s*микшер)", low)
    )
    is_realtek_builtin = "realtek" in low and not is_usb
    return {
        "usb": is_usb,
        "mic": is_mic,
        "line": is_line,
        "stereo_mix": is_stereo_mix,
        "realtek": is_realtek_builtin,
    }


def classify_mic_strength(rms: float, peak: float) -> str:
    if peak >= 0.95 and rms >= 0.04:
        return "hot"
    if peak >= 0.95 and rms < 0.02:
        return "spiky"
    if rms < 0.0008 or peak < 0.004:
        return "weak"
    return "normal"


def _api_probe_priority(api: str, flags: dict[str, bool]) -> int:
    """Lower = probe earlier. Prefer WASAPI; WDM-KS often dies after the probe stream closes."""
    usb = 0 if flags.get("usb") else 20
    if "WASAPI" in api:
        return usb + 0
    if "WDM-KS" in api:
        return usb + 2
    if "DirectSound" in api:
        return usb + 5
    if "MME" in api:
        return usb + 6
    return usb + 8


def _score_entry(api: str, flags: dict[str, bool], rms: float, peak: float, strength: str) -> float:
    score = 0.0
    if "WASAPI" in api:
        score += 8
    elif "WDM-KS" in api:
        score += 1
    elif "DirectSound" in api:
        score += 1

    if flags["usb"] and flags["mic"]:
        score += 12
    elif flags["usb"]:
        score += 8
    elif flags["mic"]:
        score += 4

    if flags["usb"] and strength == "normal":
        score += 10
    if flags["usb"] and "WDM-KS" in api and strength in ("normal", "weak"):
        score += 3

    if flags["line"]:
        score -= 18
    if flags["stereo_mix"]:
        score -= 25
    if flags["realtek"] and not flags["usb"]:
        score -= 6

    if peak < 1e-5 and rms < 1e-5:
        score -= 30
    elif strength == "spiky":
        score -= 20
    elif strength == "hot":
        score -= 8
    elif strength == "weak":
        if flags["usb"]:
            score += 3
        else:
            score -= 2
    else:
        score += min(8.0, max(0.0, (math.log10(max(rms, 1e-9)) + 5.0) * 2.5))
        if peak >= 0.008:
            score += 3
        elif peak >= 0.002:
            score += 1
    return score


def _probe_one(index: int, name: str, api: str, sr: int, flags: dict, seconds: float) -> dict:
    entry: dict = {
        "index": index,
        "name": name,
        "api": api,
        "sr": sr,
        "ok": False,
        "rms": 0.0,
        "peak": 0.0,
        "score": -100.0,
        "strength": "unknown",
        "flags": flags,
        "error": "",
    }
    try:
        # Callback capture: blocking sd.rec leaves WDM-KS devices unusable afterward.
        import threading

        chunks: list[np.ndarray] = []
        done = threading.Event()
        need = max(1, int(seconds / 0.05))

        def _cb(indata, frames, time_info, status):  # noqa: ARG001
            chunks.append(indata[:, 0].copy())
            if len(chunks) >= need:
                done.set()

        with sd.InputStream(
            samplerate=sr,
            channels=1,
            dtype="float32",
            blocksize=max(64, int(sr * 0.05)),
            device=index,
            callback=_cb,
        ):
            if not done.wait(seconds + 1.5):
                raise RuntimeError("probe timeout")
        if not chunks:
            raise RuntimeError("no probe audio")
        x = np.clip(np.concatenate(chunks), -1.0, 1.0)
        rms = _safe_rms(x)
        peak = float(np.max(np.abs(x)))
        strength = classify_mic_strength(rms, peak)
        entry.update(
            ok=True,
            rms=rms,
            peak=peak,
            strength=strength,
            score=_score_entry(api, flags, rms, peak, strength),
        )
    except Exception as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["score"] = -50
    return entry


def probe_inputs(seconds: float = 0.55) -> list[dict]:
    hostapis = sd.query_hostapis()
    candidates: list[tuple[int, dict, str, str, int, dict]] = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] < 1:
            continue
        api = hostapis[d["hostapi"]]["name"]
        name = str(d["name"])
        sr = int(d["default_samplerate"] or 44100)
        flags = _name_flags(name)
        candidates.append((i, d, name, api, sr, flags))

    # Probe preferred APIs first so WDM-KS USB is not locked by earlier MME/WASAPI opens.
    candidates.sort(key=lambda c: (_api_probe_priority(c[3], c[5]), c[0]))

    results: list[dict] = []
    found_good_usb = False
    for index, _d, name, api, sr, flags in candidates:
        # Once we have a healthy USB, skip near-duplicate weak hosts (MME/DS).
        if found_good_usb and flags.get("usb") and ("MME" in api or "DirectSound" in api):
            results.append(
                {
                    "index": index,
                    "name": name,
                    "api": api,
                    "sr": sr,
                    "ok": False,
                    "rms": 0.0,
                    "peak": 0.0,
                    "score": -40.0,
                    "strength": "skipped",
                    "flags": flags,
                    "error": "skipped after good USB found",
                }
            )
            continue

        entry = _probe_one(index, name, api, sr, flags, seconds)
        results.append(entry)
        if entry.get("ok") and flags.get("usb") and entry.get("strength") == "normal" and "WASAPI" in api:
            found_good_usb = True
            break

    # Fill placeholders for unprobed devices so callers still see the list.
    probed_idx = {int(r["index"]) for r in results}
    for index, _d, name, api, sr, flags in candidates:
        if index in probed_idx:
            continue
        results.append(
            {
                "index": index,
                "name": name,
                "api": api,
                "sr": sr,
                "ok": False,
                "rms": 0.0,
                "peak": 0.0,
                "score": -45.0,
                "strength": "skipped",
                "flags": flags,
                "error": "skipped after good USB found",
            }
        )

    # Retry only if we never found a healthy USB.
    if not any(
        r.get("ok") and (r.get("flags") or {}).get("usb") and r.get("strength") == "normal"
        for r in results
    ):
        time.sleep(0.25)
        for i, entry in enumerate(results):
            flags = entry.get("flags") or {}
            if not flags.get("usb"):
                continue
            if "WDM-KS" not in str(entry.get("api") or ""):
                continue
            if entry.get("error") == "skipped after good USB found":
                continue
            retry = _probe_one(
                int(entry["index"]),
                str(entry["name"]),
                str(entry["api"]),
                int(entry["sr"] or 44100),
                flags,
                seconds,
            )
            if retry.get("ok") and retry.get("score", -100) > entry.get("score", -100):
                results[i] = retry

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def pick_best(results: list[dict] | None = None) -> dict | None:
    results = results if results is not None else probe_inputs()
    ok = [r for r in results if r.get("ok") and r.get("score", -100) > -10]
    if not ok:
        ok = [r for r in results if r.get("ok")]
    if not ok:
        return results[0] if results else None

    strength_rank = {"normal": 3, "weak": 2, "hot": 1, "spiky": 0, "unknown": 1, "skipped": 0}

    def key(r: dict) -> tuple:
        flags = r.get("flags") or {}
        usb = 1 if flags.get("usb") else 0
        api = str(r.get("api") or "")
        wasapi = 1 if "WASAPI" in api else 0
        return (
            usb,
            wasapi,
            float(r.get("score", -100)),
            strength_rank.get(str(r.get("strength") or "unknown"), 0),
            float(r.get("rms") or 0.0),
            float(r.get("peak") or 0.0),
        )

    usb_ok = [r for r in ok if (r.get("flags") or {}).get("usb")]
    pool = usb_ok or ok
    return max(pool, key=key)


def suggested_input_gain(strength: str, rms: float) -> float:
    if strength == "weak" or rms < 0.0008:
        target = 0.025
        g = target / max(rms, 1e-6)
        return float(min(max(g, 25.0), 200.0))
    if strength == "normal" and rms < 0.02:
        # Keep amplified ambient low so speech has headroom above the gate.
        return float(min(max(0.02 / max(rms, 1e-4), 1.2), 6.0))
    return 1.0


if __name__ == "__main__":
    rows = probe_inputs()
    best = pick_best(rows)
    out = {"devices": rows, "best": best}
    if best and best.get("ok"):
        out["suggestedGain"] = suggested_input_gain(best.get("strength", "normal"), best["rms"])
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)
