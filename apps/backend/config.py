from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

FridayStatus = Literal["idle", "listening", "thinking", "speaking", "error"]
LLMProviderName = Literal["openai", "anthropic", "google", "qwen", "ollama"]

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "FRIDAY"
CONFIG_FILE = APP_DATA_DIR / "config.json"

# Secrets live in .env only — never overwritten by empty config.json values.
_SECRET_KEYS = frozenset(
    {
        "openai_api_key",
        "qwen_api_key",
        "anthropic_api_key",
        "google_api_key",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: LLMProviderName = "ollama"
    llm_model: str = "qwen2.5:3b"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    openai_api_key: str = ""
    qwen_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    wake_word_enabled: bool = True
    wake_word: str = "пятница"
    tts_voice: str = "ru-RU-SvetlanaNeural"
    stt_model: str = "tiny"

    autostart: bool = True
    splash_duration_ms: int = 2500
    backend_host: str = "127.0.0.1"
    backend_port: int = 8765

    data_dir: Path = APP_DATA_DIR
    audio_dir: Path = APP_DATA_DIR / "audio"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def to_client_config(self) -> dict:
        # No API keys exposed to the desktop UI.
        return {
            "llmProvider": self.llm_provider,
            "llmModel": self.llm_model,
            "llmBaseUrl": self.llm_base_url,
            "wakeWordEnabled": self.wake_word_enabled,
            "wakeWord": self.wake_word,
            "ttsVoice": self.tts_voice,
            "sttModel": self.stt_model,
            "autostart": self.autostart,
            "splashDurationMs": self.splash_duration_ms,
            "hasQwenKey": bool(self.qwen_api_key or self.openai_api_key),
            "ollamaReady": self.llm_provider == "ollama",
        }

    def save(self) -> None:
        self.ensure_dirs()
        # Persist non-secret prefs only; keys stay in .env.
        payload = {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "wake_word_enabled": self.wake_word_enabled,
            "wake_word": self.wake_word,
            "tts_voice": self.tts_voice,
            "stt_model": self.stt_model,
            "autostart": self.autostart,
            "splash_duration_ms": self.splash_duration_ms,
        }
        CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> Settings:
        settings = cls()
        settings.ensure_dirs()
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
            for key, value in data.items():
                if key in _SECRET_KEYS:
                    continue
                if hasattr(settings, key) and value is not None and value != "":
                    setattr(settings, key, value)
        return settings

    def update_from_client(self, data: dict) -> None:
        mapping = {
            "llmProvider": "llm_provider",
            "llmModel": "llm_model",
            "llmBaseUrl": "llm_base_url",
            "wakeWordEnabled": "wake_word_enabled",
            "wakeWord": "wake_word",
            "ttsVoice": "tts_voice",
            "sttModel": "stt_model",
            "autostart": "autostart",
            "splashDurationMs": "splash_duration_ms",
        }
        for client_key, attr in mapping.items():
            if client_key not in data:
                continue
            # Ignore any legacy key fields from older UI builds.
            if "ApiKey" in client_key:
                continue
            setattr(self, attr, data[client_key])
        self.save()


settings = Settings.load()
