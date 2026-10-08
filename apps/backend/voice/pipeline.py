from __future__ import annotations

import asyncio
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Awaitable

import edge_tts
import numpy as np
import sounddevice as sd

from config import Settings
from voice.mic_probe import pick_best, probe_inputs, suggested_input_gain

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore


MIN_AUDIO_SEC = 0.55
SPEAKING_COOLDOWN_SEC = 1.4
TARGET_SR = 16000
SESSION_HOLD_SEC = 18.0
ECHO_GUARD_SEC = 8.0
TRANSCRIPT_COOLDOWN_SEC = 1.2


def _resample(x: np.ndarray, orig_sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    if orig_sr == target_sr or len(x) == 0:
        return x.astype(np.float32, copy=False)
    n = max(1, int(round(len(x) * target_sr / orig_sr)))
    xp = np.linspace(0.0, 1.0, num=len(x), endpoint=False)
    fp = x.astype(np.float64)
    x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
    return np.interp(x_new, xp, fp).astype(np.float32)


def _despike(x: np.ndarray) -> np.ndarray:
    """Kill rare full-scale WDM-KS glitches that wreck VAD/STT."""
    abs_x = np.abs(x)
    peak = float(np.max(abs_x)) if len(abs_x) else 0.0
    if peak < 0.85:
        return x
    lim = max(float(np.percentile(abs_x, 99.0)) * 3.5, 0.08)
    lim = min(lim, 0.95)
    return np.clip(x, -lim, lim).astype(np.float32)


def _agc(x: np.ndarray, target_peak: float = 0.45, max_gain: float = 120.0) -> np.ndarray:
    peak = float(np.max(np.abs(x))) + 1e-8
    gain = min(target_peak / peak, max_gain)
    return np.clip(x * gain, -1.0, 1.0).astype(np.float32)


class VoicePipeline:
    def __init__(
        self,
        settings: Settings,
        on_status: Callable[[str], Awaitable[None]],
        on_transcript: Callable[[str], Awaitable[None]],
        on_audio: Callable[[str], Awaitable[None]],
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.settings = settings
        self.on_status = on_status
        self.on_transcript = on_transcript
        self.on_audio = on_audio
        self.on_event = on_event
        self._enabled = True
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._whisper: WhisperModel | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._busy = threading.Event()
        self._muted_until = 0.0
        self.mic_info: dict[str, Any] = {}
        self.speech_rms = 0.012
        self.silence_rms = 0.006
        self.input_gain = 1.0
        self._noise_ema = 0.002
        self._session_until = 0.0
        self._last_spoken = ""
        self._last_spoken_at = 0.0
        self._last_transcript = ""
        self._last_transcript_at = 0.0
        self._speaking_hard = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled and not (self._thread and self._thread.is_alive()):
            self.start()
        elif not enabled:
            self.stop()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="friday-voice")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def mute_for(self, seconds: float) -> None:
        self._muted_until = max(self._muted_until, time.time() + max(seconds, 0))

    def release(self) -> None:
        self._busy.clear()
        self._speaking_hard = False
        # Keep a short mute tail so TTS tail / speakers don't re-trigger STT.
        self.mute_for(0.9)
        if self._enabled and not self._stop.is_set():
            self._emit_status("listening")

    def note_spoken(self, text: str) -> None:
        self._last_spoken = (text or "").strip().lower()
        self._last_spoken_at = time.time()
        self._speaking_hard = True
        est = max(1.6, min(40.0, len(self._last_spoken) / 10.0 + 1.2))
        self.mute_for(est + SPEAKING_COOLDOWN_SEC)

    def _recover_after_error(self, delay: float = 0.8) -> None:
        def _go() -> None:
            time.sleep(delay)
            if self._enabled and not self._stop.is_set():
                self.release()

        threading.Thread(target=_go, daemon=True, name="friday-voice-recover").start()

    def _emit_status(self, status: str) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.on_status(status), self._loop)

    def _emit_transcript(self, text: str) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.on_transcript(text), self._loop)

    def _emit_audio(self, path: str) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.on_audio(path), self._loop)

    def _emit_event(self, payload: dict[str, Any]) -> None:
        if self.on_event and self._loop:
            asyncio.run_coroutine_threadsafe(self.on_event(payload), self._loop)

    def _get_whisper(self) -> WhisperModel:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed")
        if self._whisper is None:
            model_name = self.settings.stt_model or "base"
            print(f"[voice] loading whisper model={model_name}")
            self._whisper = WhisperModel(model_name, device="cpu", compute_type="int8")
            print("[voice] whisper ready")
        return self._whisper

    def _select_and_calibrate(self) -> tuple[int, int]:
        print("[voice] probing microphones…")
        time.sleep(0.35)
        ranked = probe_inputs(0.5)
        print(
            "[voice] probe top: "
            + ", ".join(
                f"#{r['index']} score={r['score']:.0f} rms={r['rms']:.5f} {r.get('strength')}"
                for r in ranked[:6]
                if r.get("ok")
            )
        )

        candidates = [r for r in ranked if r.get("ok") and r.get("score", -100) > -10]
        if not candidates:
            candidates = [r for r in ranked if r.get("ok")]
        if not candidates:
            raise RuntimeError("No working microphone found")

        # Prefer pick_best ordering, then remaining by score.
        primary = pick_best(ranked)
        ordered: list[dict] = []
        if primary and primary.get("ok"):
            ordered.append(primary)
        for r in sorted(candidates, key=lambda x: float(x.get("score", -100)), reverse=True):
            if ordered and int(r["index"]) == int(ordered[0]["index"]):
                continue
            ordered.append(r)

        last_err: Exception | None = None
        for best in ordered[:8]:
            device = int(best["index"])
            sr = int(best["sr"] or 44100)
            strength = str(best.get("strength") or "normal")
            gain = suggested_input_gain(strength, float(best.get("rms") or 1e-5))
            # Do not open/close another test stream here — on WDM-KS that
            # invalidates the next listen InputStream. Trust callback probe.
            self.input_gain = gain
            probe_noise = float(best.get("rms") or 1e-5) * gain
            noise = probe_noise
            min_speech = 0.006 if gain >= 25 else 0.0008
            min_sil = 0.003 if gain >= 25 else 0.0004
            speech_mul = 2.2 if gain >= 25 else 1.45
            self.silence_rms = float(np.clip(noise * 1.25, min_sil, 0.03))
            self.speech_rms = float(
                np.clip(max(noise * speech_mul, self.silence_rms * 1.35), min_speech, 0.045)
            )
            self._noise_ema = noise
            self.mic_info = {
                "index": device,
                "name": best["name"],
                "api": best["api"],
                "sr": sr,
                "probeRms": best["rms"],
                "probePeak": best["peak"],
                "score": best["score"],
                "strength": strength,
                "inputGain": self.input_gain,
                "noiseFloor": noise,
                "speechRms": self.speech_rms,
                "silenceRms": self.silence_rms,
            }
            print(
                f"[voice] selected mic #{device} {best['name']!r} "
                f"api={best['api']} strength={strength} gain={gain:.1f}x "
                f"rms={float(best.get('rms') or 0):.5f} peak={float(best.get('peak') or 0):.5f}"
            )
            print(
                f"[voice] calibrated noise={noise:.5f} "
                f"speech_gate={self.speech_rms:.5f} silence_gate={self.silence_rms:.5f}"
            )
            self._emit_event({"type": "mic_info", "mic": self.mic_info})
            time.sleep(0.35)
            return device, sr

        raise RuntimeError(f"No openable microphone stream ({last_err})")

    def _wake_aliases(self) -> set[str]:
        raw = (self.settings.wake_word or "пятница").strip().lower()
        return {
            raw,
            "пятница",
            "пятницу",
            "пятнице",
            "пятницы",
            "пятниц",
            "пятниса",
            "пятнца",
            "пиатница",
            "пятницв",
            "friday",
            "fridei",
            "frayday",
            "fridey",
            "fride",
        }

    def _fuzzy_wake(self, text: str) -> bool:
        tokens = re.findall(r"[а-яёa-z]+", (text or "").lower())
        targets = {a for a in self._wake_aliases() if len(a) >= 4}
        for tok in tokens[:6]:
            if len(tok) < 4:
                continue
            for alias in targets:
                if tok == alias or tok.startswith(alias[:5]) or alias.startswith(tok[:5]):
                    return True
                if abs(len(tok) - len(alias)) > 3:
                    continue
                dist = self._lev(tok, alias)
                if dist <= 2:
                    return True
        return False

    @staticmethod
    def _lev(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]

    def _contains_wake(self, text: str) -> bool:
        low = (text or "").lower()
        for alias in sorted(self._wake_aliases(), key=len, reverse=True):
            if re.search(rf"(?i)(?<!\w){re.escape(alias)}(?!\w)", low):
                return True
        return self._fuzzy_wake(text)

    def _strip_wake(self, text: str) -> str:
        cleaned = text
        for alias in sorted(self._wake_aliases(), key=len, reverse=True):
            cleaned = re.sub(
                rf"(?i)(?<!\w){re.escape(alias)}(?!\w)[,!.\s]*",
                " ",
                cleaned,
                count=1,
            )
        return re.sub(r"\s+", " ", cleaned).strip(" .,!?:;—-\t")

    def _normalize_command(self, text: str) -> str | None:
        original = (text or "").strip()
        if len(original) < 2:
            return None
        low = original.lower()
        junk = {
            "субтитры",
            "подписывайтесь",
            "продолжение следует",
            "редактор субтитров",
            "music",
            "thanks for watching",
            "thank you",
            "thanks",
            "applause",
            "смех",
            "аплодисменты",
        }
        if any(j in low for j in junk) and len(original) < 48:
            return None
        greetings = {
            "привет",
            "приветик",
            "здравствуй",
            "здравствуйте",
            "hello",
            "hi",
            "hey",
            "алло",
            "слушай",
            "слушаю",
            "да",
            "нет",
            "угу",
            "ага",
        }
        stripped = self._strip_wake(original)
        stripped_low = stripped.lower().strip(" .,!?:;—-\t")
        # Lone greetings / echo of our own TTS — never feed the chat loop.
        if stripped_low in greetings or low in greetings:
            return None
        if len(stripped_low) < 3:
            return None
        if self._is_echo(stripped_low):
            return None
        return stripped or None

    def _is_echo(self, text: str) -> bool:
        if not text or not self._last_spoken:
            return False
        if time.time() - self._last_spoken_at > ECHO_GUARD_SEC:
            return False
        spoken = self._last_spoken
        if text == spoken or text in spoken or spoken in text:
            return True
        # Share first token with recent TTS (привет / слушаю loops).
        a = text.split()[:2]
        b = spoken.split()[:2]
        return bool(a and b and a[0] == b[0] and len(text) < 28)

    def _run_loop(self) -> None:
        try:
            device, capture_sr = self._select_and_calibrate()
        except Exception as exc:
            print(f"[voice] mic select failed: {exc}")
            self._emit_status("error")
            self._recover_after_error(2.0)
            return

        chunk_duration = 0.05
        chunk_samples = int(capture_sr * chunk_duration)
        max_silence = int(2.0 / chunk_duration)
        max_record = int(14.0 / chunk_duration)
        min_frames = int(MIN_AUDIO_SEC / chunk_duration)

        recording: list[np.ndarray] = []
        silence_frames = 0
        speaking = False

        self._emit_status("listening")
        try:
            self._get_whisper()
        except Exception as exc:
            print(f"[voice] whisper preload failed: {exc}")

        def callback(indata, frames, time_info, status):  # noqa: ARG001
            nonlocal recording, silence_frames, speaking
            if self._stop.is_set() or not self._enabled:
                return
            if self._busy.is_set() or self._speaking_hard or time.time() < self._muted_until:
                speaking = False
                recording = []
                silence_frames = 0
                return

            audio = _despike(np.clip(indata[:, 0].astype(np.float32) * self.input_gain, -1.0, 1.0))
            rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2) + 1e-12))

            if not speaking:
                # Track ambient so quiet USB speech still crosses the gate.
                self._noise_ema = 0.92 * self._noise_ema + 0.08 * rms
                min_speech = 0.01 if self.input_gain >= 25 else 0.0012
                min_sil = 0.005 if self.input_gain >= 25 else 0.0006
                speech_mul = 2.8 if self.input_gain >= 25 else 1.7
                self.silence_rms = float(np.clip(self._noise_ema * 1.25, min_sil, 0.03))
                self.speech_rms = float(
                    np.clip(
                        max(self._noise_ema * speech_mul, self.silence_rms * 1.35),
                        min_speech,
                        0.045,
                    )
                )
                if rms >= self.speech_rms:
                    speaking = True
                    recording = [audio]
                    silence_frames = 0
                return

            recording.append(audio)
            if rms < self.silence_rms:
                silence_frames += 1
            else:
                silence_frames = 0

            too_long = len(recording) >= max_record
            ended = silence_frames >= max_silence and len(recording) > min_frames

            if ended or too_long:
                clip = np.concatenate(recording)
                recording = []
                silence_frames = 0
                speaking = False
                clip_rms = float(np.sqrt(np.mean(clip.astype(np.float64) ** 2) + 1e-12))
                if clip_rms < self.silence_rms * 0.9:
                    return
                threading.Thread(
                    target=self._process_recording,
                    args=(clip, capture_sr),
                    daemon=True,
                ).start()

        try:
            while not self._stop.is_set():
                try:
                    stream_kw: dict = {
                        "samplerate": capture_sr,
                        "channels": 1,
                        "dtype": "float32",
                        "blocksize": 0,
                        "device": device,
                        "callback": callback,
                    }
                    try:
                        if "WASAPI" in str(self.mic_info.get("api") or ""):
                            stream_kw["extra_settings"] = sd.WasapiSettings(exclusive=False)
                    except Exception:
                        pass
                    with sd.InputStream(**stream_kw):
                        print(f"[voice] listening on device={device} sr={capture_sr}")
                        self._emit_status("listening")
                        while not self._stop.is_set():
                            time.sleep(0.1)
                except Exception as exc:
                    print(f"[voice] mic error: {exc}")
                    self._emit_status("error")
                    self._busy.clear()
                    if self._stop.is_set():
                        break
                    time.sleep(1.2)
                    try:
                        device, capture_sr = self._select_and_calibrate()
                        chunk_samples = int(capture_sr * chunk_duration)
                    except Exception as exc2:
                        print(f"[voice] reselect failed: {exc2}")
                    recording = []
                    silence_frames = 0
                    speaking = False
        except Exception as exc:
            print(f"[voice] fatal: {exc}")
            self._emit_status("error")
            self._recover_after_error(1.0)

    def inject_pcm(self, audio: np.ndarray, capture_sr: int) -> None:
        """Test/helper: run the same path as a finished mic utterance."""
        threading.Thread(
            target=self._process_recording,
            args=(audio.astype(np.float32), capture_sr),
            daemon=True,
        ).start()

    def _process_recording(self, audio: np.ndarray, capture_sr: int) -> None:
        if self._busy.is_set() or self._speaking_hard:
            return
        now = time.time()
        if now - self._last_transcript_at < TRANSCRIPT_COOLDOWN_SEC:
            return
        self._busy.set()
        held_for_chat = False
        try:
            self._emit_status("thinking")
            audio16 = _resample(_despike(audio), capture_sr, TARGET_SR)
            audio16 = _agc(audio16)
            model = self._get_whisper()
            segments, info = model.transcribe(
                audio16,
                language="ru",
                vad_filter=False,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt="Пятница открой Steam. Какая погода.",
            )
            segs = list(segments)
            text = " ".join(s.text.strip() for s in segs).strip()
            if getattr(info, "language_probability", 1.0) < 0.22 and len(text) < 5:
                text = ""

            if not text:
                print("[voice] empty/noise: ''")
                self._emit_status("listening")
                return

            if self._is_echo(text.lower()):
                print(f"[voice] echo ignored: {text!r}")
                self._emit_status("listening")
                return

            has_wake = self._contains_wake(text)
            command = self._normalize_command(text)
            gated = bool(self.settings.wake_word_enabled)
            in_session = time.time() < self._session_until

            if gated and has_wake:
                self._session_until = time.time() + SESSION_HOLD_SEC
                if command:
                    if command == self._last_transcript and now - self._last_transcript_at < 6:
                        print(f"[voice] dup ignored: {command!r}")
                        self._emit_status("listening")
                        return
                    print(f"[voice] heard: {text!r} -> cmd: {command!r}")
                    self._last_transcript = command
                    self._last_transcript_at = now
                    held_for_chat = True
                    self._emit_transcript(command)
                else:
                    print(f"[voice] wake only: {text!r}")
                    held_for_chat = True
                    self._emit_event({"type": "wake_ack"})
                return

            if gated and not in_session:
                print(f"[voice] ignored (armed): {text!r}")
                self._emit_status("listening")
                return

            if command:
                if command == self._last_transcript and now - self._last_transcript_at < 6:
                    print(f"[voice] dup ignored: {command!r}")
                    self._emit_status("listening")
                    return
                self._session_until = time.time() + SESSION_HOLD_SEC
                print(f"[voice] heard: {text!r} -> cmd: {command!r}")
                self._last_transcript = command
                self._last_transcript_at = now
                held_for_chat = True
                self._emit_transcript(command)
            else:
                print(f"[voice] empty/noise: {text!r}")
                self._emit_status("listening")
        except Exception as exc:
            print(f"[voice] stt error: {exc}")
            self._emit_status("error")
            held_for_chat = False
            self._recover_after_error(0.8)
        finally:
            if not held_for_chat:
                self._busy.clear()

    async def synthesize(self, text: str) -> Path:
        self.settings.ensure_dirs()
        out_path = self.settings.audio_dir / f"tts_{uuid.uuid4().hex[:8]}.mp3"
        voice = self.settings.tts_voice or "ru-RU-SvetlanaNeural"
        communicate = edge_tts.Communicate(text, voice, rate="+12%")
        await communicate.save(str(out_path))
        return out_path

    async def speak(self, text: str) -> None:
        clean = (text or "").strip()
        if not clean:
            self.release()
            return
        if len(clean) > 280:
            clean = clean[:277].rsplit(" ", 1)[0] + "…"
        self.note_spoken(clean)
        self._busy.set()
        await self.on_status("speaking")
        try:
            path = await self.synthesize(clean)
            await self.on_audio(str(path))
            # Release only on voice_playback_done (or this fallback if UI never ACKs).
            fallback = min(14.0, max(2.4, len(clean) / 11.0 + 1.5))

            def _fallback() -> None:
                time.sleep(fallback)
                if self._speaking_hard:
                    self.release()

            threading.Thread(target=_fallback, daemon=True, name="friday-tts-fallback").start()
        except Exception as exc:
            print(f"[voice] tts error: {exc}")
            await self.on_status("error")
            self.release()
