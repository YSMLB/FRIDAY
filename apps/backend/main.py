from __future__ import annotations

import asyncio
import json
import threading
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.friday import FridayAgent
from config import settings
from voice.pipeline import VoicePipeline

agent = FridayAgent(settings)
voice: VoicePipeline | None = None
_voice_lock = threading.Lock()
connected_clients: set[WebSocket] = set()
status: str = "idle"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_dirs()
    loop = asyncio.get_running_loop()
    init_voice(loop)
    yield
    if voice:
        voice.stop()


app = FastAPI(title="FRIDAY Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def broadcast(message: dict) -> None:
    dead: set[WebSocket] = set()
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)


async def set_status(new_status: str) -> None:
    global status
    status = new_status
    await broadcast({"type": "status", "status": new_status})


def init_voice(loop: asyncio.AbstractEventLoop) -> VoicePipeline:
    global voice
    with _voice_lock:
        if voice is not None:
            voice.bind_loop(loop)
            if not voice._thread or not voice._thread.is_alive():
                voice.start()
            return voice

        async def on_transcript(text: str) -> None:
            await broadcast({"type": "voice_transcript", "text": text})
            await handle_chat(text, speak=True)

        async def on_audio(path: str) -> None:
            await broadcast({"type": "audio_ready", "path": path})

        async def on_event(payload: dict) -> None:
            await broadcast(payload)
            if payload.get("type") == "wake_ack" and voice:
                asyncio.create_task(voice.speak("Слушаю"))

        voice = VoicePipeline(settings, set_status, on_transcript, on_audio, on_event)
        voice.bind_loop(loop)
        voice.start()
        return voice


async def handle_chat(content: str, speak: bool = True) -> None:
    await set_status("thinking")
    full = ""

    async def on_delta(delta: str) -> None:
        nonlocal full
        full += delta
        await broadcast({"type": "chat_delta", "content": delta})

    async def on_tool(name: str, args: dict) -> None:
        await broadcast({"type": "tool_call", "name": name, "args": args})

    async def on_confirm(action_id: str, message: str) -> None:
        await broadcast({"type": "confirm_request", "actionId": action_id, "message": message})

    try:
        from tools.registry import CONFIRM_TOOLS, execute_tool
        from voice.intents import match_intent

        intent = match_intent(content)
        if intent:
            await on_tool(intent["name"], intent["args"])
            action_id = str(uuid.uuid4()) if intent["name"] in CONFIRM_TOOLS else None
            result, needs = await execute_tool(intent["name"], intent["args"], action_id)
            if needs and action_id:
                await on_confirm(action_id, f"Подтверди {intent['name']}: {intent['args']}")
                if voice:
                    voice.release()
                return
            await broadcast({"type": "chat_done", "content": result})
            if speak and voice and result:
                await voice.speak(result)
            elif voice:
                voice.release()
            else:
                await set_status("idle")
            if intent["name"] == "quit_friday":
                await broadcast({"type": "app_quit"})
            return

        result = await agent.run(content, on_delta, on_tool, on_confirm)
        await broadcast({"type": "chat_done", "content": result or full})
        reply = (result or full or "").strip()
        if speak and voice and reply:
            await voice.speak(reply)
        else:
            if voice:
                voice.release()
            else:
                await set_status("idle")
    except Exception as exc:
        await broadcast({"type": "chat_error", "error": str(exc)})
        await set_status("error")
        await asyncio.sleep(1)
        if voice:
            voice.release()
        else:
            await set_status("idle")


@app.get("/health")
async def health():
    payload = {
        "status": "ok",
        "service": "friday",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
    }
    if voice and voice.mic_info:
        payload["mic"] = voice.mic_info
    return payload


@app.get("/voice/diag")
async def voice_diag():
    from voice.mic_probe import probe_inputs, pick_best

    devices = probe_inputs(0.5)
    best = pick_best(devices)
    return {
        "devices": devices,
        "best": best,
        "active": voice.mic_info if voice else None,
        "status": status,
    }


@app.post("/voice/selftest")
async def voice_selftest():
    """Inject clean TTS audio into the STT→chat→speak path (no room mic needed)."""
    import shutil
    import subprocess
    import tempfile
    import wave
    from pathlib import Path

    import edge_tts
    import numpy as np

    loop = asyncio.get_running_loop()
    global voice
    if voice is None:
        init_voice(loop)

    phrase = "Пятница, скажи коротко что два плюс два"
    ffmpeg = shutil.which("ffmpeg") or (
        r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages"
        r"\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-N-125875-g5d4d3bdc61-win64-gpl\bin\ffmpeg.exe"
    )
    with tempfile.TemporaryDirectory() as td:
        mp3 = Path(td) / "in.mp3"
        wav = Path(td) / "in.wav"
        await edge_tts.Communicate(phrase, "ru-RU-SvetlanaNeural").save(str(mp3))
        subprocess.run(
            [ffmpeg, "-y", "-i", str(mp3), "-ac", "1", "-ar", "16000", str(wav)],
            check=True,
            capture_output=True,
        )
        with wave.open(str(wav), "rb") as w:
            frames = w.readframes(w.getnframes())
            sr = w.getframerate()
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    assert voice is not None
    voice.release()
    voice.inject_pcm(audio, int(sr))
    return {
        "ok": True,
        "phrase": phrase,
        "samples": int(len(audio)),
        "sr": int(sr),
        "mic": voice.mic_info,
    }


class AppOpenBody(BaseModel):
    name: str = ""


class WebOpenBody(BaseModel):
    url: str = ""


@app.get("/system/hud")
async def system_hud():
    from tools.hud import snapshot

    return snapshot()


@app.get("/system/library")
async def system_library():
    from tools.library import library_snapshot

    return library_snapshot()


class LaunchBody(BaseModel):
    target: str = ""


@app.post("/apps/launch")
async def apps_launch(payload: LaunchBody):
    from tools.system import open_launch_target

    result = open_launch_target(payload.target)
    await broadcast({"type": "tool_call", "name": "open_app", "args": {"target": payload.target}})
    return {"ok": True, "result": result}


@app.post("/apps/open")
async def apps_open(payload: AppOpenBody):
    from tools.system import open_app

    name = payload.name
    result = open_app(name)
    await broadcast({"type": "tool_call", "name": "open_app", "args": {"name": name}})
    return {"ok": True, "result": result}


@app.post("/web/open")
async def web_open(payload: WebOpenBody):
    import webbrowser

    if payload.url:
        webbrowser.open(payload.url)
    return {"ok": True}


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    path = settings.audio_dir / filename
    if not path.exists():
        return {"error": "not found"}
    return FileResponse(path, media_type="audio/mpeg")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    loop = asyncio.get_running_loop()
    global voice
    if voice is None:
        init_voice(loop)
    else:
        # Recover stuck FAULT / dead mic thread on reconnect
        if not voice._thread or not voice._thread.is_alive():
            voice.start()
        voice.release()

    await ws.send_json({"type": "status", "status": "listening"})
    await ws.send_json({"type": "config", "config": settings.to_client_config()})
    if voice and voice.mic_info:
        await ws.send_json({"type": "mic_info", "mic": voice.mic_info})

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "chat":
                asyncio.create_task(handle_chat(msg.get("content", ""), speak=True))
            elif msg_type == "get_config":
                await ws.send_json({"type": "config", "config": settings.to_client_config()})
            elif msg_type == "update_config":
                settings.update_from_client(msg.get("config", {}))
                if voice:
                    voice.settings = settings
                    voice.set_enabled(True)
                await broadcast({"type": "config", "config": settings.to_client_config()})
            elif msg_type == "get_status":
                await ws.send_json({"type": "status", "status": status})
            elif msg_type == "voice_toggle":
                if voice:
                    enabled = msg.get("enabled", True)
                    voice.set_enabled(enabled)
                    if enabled:
                        await set_status("listening")
            elif msg_type == "voice_playback_done":
                if voice:
                    voice.release()
            elif msg_type == "open_app":
                from tools.system import open_launch_target

                name = msg.get("name") or msg.get("target") or ""
                result = open_launch_target(name)
                await broadcast({"type": "tool_call", "name": "open_app", "args": {"name": name}})
                await ws.send_json({"type": "chat_done", "content": result})
            elif msg_type == "web_open":
                import webbrowser

                url = msg.get("url") or ""
                if url:
                    webbrowser.open(url)
            elif msg_type == "quit_app":
                await broadcast({"type": "app_quit"})
            elif msg_type == "confirm_action":
                result = agent.handle_confirmation(msg.get("actionId", ""), msg.get("confirmed", False))
                await ws.send_json({"type": "chat_done", "content": result})
                if voice and result:
                    asyncio.create_task(voice.speak(result))
    except WebSocketDisconnect:
        connected_clients.discard(ws)


def main():
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
