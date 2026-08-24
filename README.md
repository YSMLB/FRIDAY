# FRIDAY — AI Assistant

JARVIS-style desktop AI assistant for Windows. Voice + text interface powered by your choice of LLM (OpenAI, Anthropic, Google Gemini).

## Features

- **Text chat** with streaming LLM responses
- **Voice pipeline**: wake word, speech-to-text (Whisper), text-to-speech (Edge TTS)
- **PC tools**: open apps, volume control, web search, system power (with confirmation)
- **JARVIS HUD**: dark cyan theme, animated rings, splash screen on startup
- **System tray**: minimize to tray, background operation
- **Autostart**: launch on Windows boot
- **Multi-provider LLM**: switch OpenAI / Anthropic / Google in settings

## Документация на русском

Подробно: как устроен проект, как собран и как запустить — см. **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**.

## Quick Start

### 1. Install dependencies

```powershell
# From project root
npm run install:all
```

API key уже в `.env` (Google Gemini). Если файла нет:

```powershell
copy .env.example .env
```

### 2. Run in development

```powershell
npm run dev
```

This starts the Python backend (port 8765) and Electron desktop app.

### 3. Configure LLM

Open Settings (gear icon) and set:
- LLM Provider (openai / anthropic / google)
- Model name
- API key for your provider

### 4. Enable autostart (optional)

```powershell
npm run autostart:install
```

To remove:

```powershell
npm run autostart:remove
```

## Project Structure

```
friday/
├── apps/
│   ├── backend/          # Python FastAPI — LLM, voice, tools
│   └── desktop/          # Electron + React — JARVIS UI
├── packages/
│   └── shared/           # WebSocket protocol types
├── scripts/
│   ├── install-autostart.ps1
│   └── start-friday.ps1
└── .env.example
```

## Backend API

- `GET /health` — health check
- `WS /ws` — WebSocket for chat, config, voice status
- `GET /audio/{filename}` — TTS audio files

## Voice Commands

With wake word enabled, say **"Friday"** then your command. Example:

> Friday, открой Chrome

> Friday, установи громкость на 50

Push-to-talk fallback: use the text chat if wake word is unavailable.

## Requirements

- Windows 10/11
- Node.js 18+
- Python 3.11+
- Microphone (for voice)

## Build

```powershell
cd apps/desktop
npm run electron:build
```

Output in `apps/desktop/release/`.

## Config Storage

API keys and settings are stored in `%APPDATA%/FRIDAY/config.json`.

## License

MIT
