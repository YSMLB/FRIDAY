"""E2E: websocket + /voice/selftest must yield transcript, reply, audio."""
from __future__ import annotations

import asyncio
import json
import time
import urllib.request

import websockets


async def main() -> int:
    async with websockets.connect("ws://127.0.0.1:8765/ws") as ws:
        mic = None
        deadline = time.time() + 60
        while time.time() < deadline and mic is None:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
            except asyncio.TimeoutError:
                with urllib.request.urlopen("http://127.0.0.1:8765/health") as r:
                    h = json.loads(r.read().decode())
                    if h.get("mic"):
                        mic = h["mic"]
                        print("health_mic", mic.get("index"), mic.get("strength"), mic.get("inputGain"))
                        break
                continue
            if msg.get("type") == "mic_info":
                mic = msg["mic"]
                print(
                    "MIC",
                    mic.get("index"),
                    mic.get("strength"),
                    mic.get("inputGain"),
                    mic.get("api"),
                )
                break
            print("evt", msg.get("type"), msg.get("status") or "")

        assert mic and mic.get("index") is not None, mic

        req = urllib.request.Request("http://127.0.0.1:8765/voice/selftest", method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=180) as r:
            print("selftest", r.read().decode())

        saw_tr = saw_done = saw_audio = False
        for _ in range(120):
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=180))
            t = msg.get("type")
            if t == "voice_transcript":
                saw_tr = True
                print("TRANSCRIPT", msg.get("text"))
            elif t == "chat_done":
                saw_done = True
                print("DONE", (msg.get("content") or "")[:200])
            elif t == "audio_ready":
                saw_audio = True
                print("AUDIO", msg.get("path"))
            elif t == "chat_error":
                print("ERR", msg)
                return 2
            elif t == "status":
                print("status", msg.get("status"))
            if saw_tr and saw_done and saw_audio:
                break

        if not (saw_tr and saw_done and saw_audio):
            print("FAIL", saw_tr, saw_done, saw_audio)
            return 3
        print("VOICE_PIPELINE_E2E_OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
