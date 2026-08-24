"""Closed-loop voice check: pick mic, play Russian TTS, capture+STT."""
from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import edge_tts
import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from voice.mic_probe import pick_best, probe_inputs, suggested_input_gain  # noqa: E402
from voice.pipeline import _agc, _resample  # noqa: E402

FFMPEG = (
    r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages"
    r"\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-N-125875-g5d4d3bdc61-win64-gpl\bin\ffmpeg.exe"
)


async def _make_tts(path: Path, text: str) -> None:
    await edge_tts.Communicate(text, "ru-RU-SvetlanaNeural").save(str(path))


def _mp3_to_float(mp3: Path, target_sr: int) -> np.ndarray:
    wav = mp3.with_suffix(".wav")
    subprocess.run(
        [FFMPEG, "-y", "-i", str(mp3), "-ac", "1", "-ar", str(target_sr), str(wav)],
        check=True,
        capture_output=True,
    )
    with wave.open(str(wav), "rb") as w:
        assert w.getnchannels() == 1
        frames = w.readframes(w.getnframes())
        sr = w.getframerate()
    x = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if sr != target_sr:
        x = _resample(x, sr, target_sr)
    return x


async def main() -> int:
    rows = probe_inputs(0.5)
    best = pick_best(rows)
    assert best and best["ok"], "no mic"
    device = int(best["index"])
    sr = int(best["sr"])
    gain = suggested_input_gain(str(best.get("strength") or "normal"), float(best["rms"]))
    print(
        f"MIC #{device} {best['name']!r} api={best['api']} "
        f"strength={best.get('strength')} gain={gain:.1f} rms={best['rms']:.6f}"
    )

    phrase = "Привет, я Пятница. Слышишь меня?"
    with tempfile.TemporaryDirectory() as td:
        mp3 = Path(td) / "probe.mp3"
        await _make_tts(mp3, phrase)
        play = _mp3_to_float(mp3, sr)
        # Soft pad so capture includes trailing room sound
        pad = np.zeros(int(sr * 0.4), dtype=np.float32)
        play = np.concatenate([pad, play * 0.85, pad])

        print("recording while playing…")
        # Separate play/record: duplex across different host APIs fails on Windows.
        recorded: list[np.ndarray] = []

        def _capture() -> None:
            # Start slightly before playback ends padding
            frames = int(len(play) + sr * 0.3)
            rec_local = sd.rec(frames, samplerate=sr, channels=1, dtype="float32", device=device)
            sd.wait()
            recorded.append(rec_local[:, 0].copy())

        import threading
        import time

        t = threading.Thread(target=_capture, daemon=True)
        t.start()
        time.sleep(0.15)
        sd.play(play.reshape(-1, 1), samplerate=sr, blocking=True)
        t.join(timeout=30)
        if not recorded:
            print("FAIL_NO_RECORD")
            return 4
        x = np.clip(recorded[0] * gain, -1.0, 1.0)
        rms = float(np.sqrt(np.mean(x**2) + 1e-12))
        peak = float(np.max(np.abs(x)))
        print(f"CAPTURE rms={rms:.5f} peak={peak:.5f}")

        from faster_whisper import WhisperModel

        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        audio16 = _agc(_resample(x, sr, 16000))
        segments, _info = model.transcribe(audio16, language="ru", vad_filter=False, beam_size=1)
        text = " ".join(s.text.strip() for s in segments).strip()
        print("STT", repr(text))
        if rms < 0.001:
            print("FAIL_TOO_QUIET")
            return 2
        # Accept any non-empty STT OR decent capture energy (room coupling varies)
        if text or rms >= 0.008:
            print("MIC_CAPTURE_OK")
            return 0
        print("FAIL_NO_SPEECH")
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
