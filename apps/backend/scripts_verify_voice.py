"""End-to-end voice stack check: mic pick → STT → LLM → TTS."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from voice.mic_probe import pick_best, probe_inputs  # noqa: E402
from voice.pipeline import _agc, _resample  # noqa: E402


async def main() -> int:
    print("=== 1) MIC PROBE ===")
    devices = probe_inputs(0.5)
    best = pick_best(devices)
    assert best and best["ok"], "no mic"
    print("BEST", best["index"], best["name"], "rms", round(best["rms"], 5), "peak", round(best["peak"], 5))

    device = int(best["index"])
    sr = int(best["sr"])
    print("=== 2) RECORD 3.5s (speak if you want) ===")
    rec = sd.rec(int(sr * 3.5), samplerate=sr, channels=1, dtype="float32", device=device)
    sd.wait()
    x = np.clip(rec[:, 0], -1.0, 1.0)
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2) + 1e-12))
    print(f"capture rms={rms:.5f} peak={peak:.5f}")
    audio16 = _agc(_resample(x, sr, 16000))
    print(f"agc peak={float(np.max(np.abs(audio16))):.5f}")

    print("=== 3) WHISPER STT ===")
    from faster_whisper import WhisperModel

    t0 = time.time()
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio16, language="ru", vad_filter=False, beam_size=1)
    text = " ".join(s.text.strip() for s in segments).strip()
    print(f"stt in {time.time()-t0:.1f}s lang_p={getattr(info,'language_probability',None)} text={text!r}")

    print("=== 4) OLLAMA LLM ===")
    from openai import OpenAI

    client = OpenAI(api_key="ollama", base_url="http://127.0.0.1:11434/v1")
    prompt = text if len(text) >= 2 else "Привет, скажи коротко что ты Пятница"
    r = client.chat.completions.create(
        model="qwen2.5:3b",
        messages=[
            {
                "role": "system",
                "content": "Ты Пятница, ассистент женского рода. Ответь одним коротким предложением по-русски.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=80,
    )
    reply = (r.choices[0].message.content or "").strip()
    print("llm:", reply)
    assert reply, "empty llm"

    print("=== 5) EDGE TTS ===")
    import edge_tts

    out = Path(os_environ_audio())
    out.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(reply, "ru-RU-SvetlanaNeural").save(str(out))
    print("tts bytes", out.stat().st_size, out)
    assert out.stat().st_size > 500, "tts too small"

    print("=== OK voice stack ===")
    return 0


def os_environ_audio() -> Path:
    import os

    base = Path(os.environ.get("APPDATA", str(Path.home()))) / "FRIDAY" / "audio"
    return base / "verify_tts.mp3"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
