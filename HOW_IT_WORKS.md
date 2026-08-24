# FRIDAY — как устроен проект и как его запустить

Документ на русском: архитектура, как собран MVP, и пошаговый запуск прямо сейчас.

---

## Что это такое

**FRIDAY** — не новая нейросеть, а **оркестратор** вокруг готовой LLM (сейчас подключён **Google Gemini**).

Ты говоришь или пишешь → FRIDAY отправляет запрос в Gemini → при необходимости вызывает инструменты (открыть приложение, громкость, поиск и т.д.) → отвечает текстом и/или голосом в JARVIS-подобном окне.

---

## Как это работает (поток данных)

```
Микрофон / текстовый чат
        ↓
 Speech-to-Text (faster-whisper)  ← только для голоса
        ↓
 Friday Agent (системный промпт + история)
        ↓
 LLM Adapter (Google / OpenAI / Anthropic)
        ↓
 Tool Executor (open_app, set_volume, web_search, system_power)
        ↓
 Ответ → Text-to-Speech (edge-tts) + HUD в Electron
```

1. **Frontend (Electron + React)** — окно HUD, splash, чат, настройки, system tray.
2. **Backend (Python FastAPI)** — WebSocket на `127.0.0.1:8765`, LLM, голос, инструменты.
3. **Связь** — WebSocket: статусы `idle | listening | thinking | speaking`, стриминг текста, TTS-аудио.

Конфиг и ключи:
- `.env` в корне проекта (файл в `.gitignore`, в git не попадает)
- копия настроек: `%APPDATA%\FRIDAY\config.json`

---

## Как был собран проект

Стек выбран под Windows-десктоп без Rust:

| Слой | Технология | Зачем |
|------|------------|--------|
| UI | Electron + React + TypeScript + Vite | Окно, tray, JARVIS-анимации |
| Backend | Python 3 + FastAPI + Uvicorn | LLM SDK, голос, tools |
| STT | faster-whisper | Локальное распознавание речи |
| TTS | edge-tts | Голосовые ответы (русский) |
| Wake word | openWakeWord | Активация словом «Friday» |
| LLM | Google Generative AI (сейчас) | Ответы и function calling |

Структура:

```
friday/
├── apps/
│   ├── backend/          # FastAPI: agent, llm, voice, tools
│   └── desktop/          # Electron + React HUD
├── packages/shared/      # Общий WebSocket-протокол (TypeScript)
├── scripts/              # autostart, start-friday.ps1
├── .env                  # Твои ключи (не коммитить!)
├── .env.example          # Шаблон без секретов
├── README.md             # Краткая справка (EN)
└── HOW_IT_WORKS.md       # Этот файл
```

Ключевые модули backend:

- `agent/friday.py` — личность FRIDAY + цикл «запрос → tools → ответ»
- `llm/` — адаптеры OpenAI / Anthropic / Google
- `tools/` — команды ПК
- `voice/pipeline.py` — wake word → запись → STT → TTS
- `main.py` — HTTP + WebSocket сервер

Frontend:

- Splash на старте → основной HUD с кольцами и чатом
- Настройки (⚙) — провайдер, модель, API keys, wake word
- Сворачивание в system tray

---

## Что уже подключено

Провайдер: **Google Gemini**  
Модель: **gemini-1.5-flash**  
API key записан в `.env` и в `%APPDATA%\FRIDAY\config.json`.

В настройках приложения провайдер должен быть **Google Gemini**.

---

## Как запустить сейчас

### Требования

- Windows 10/11  
- Node.js 18+  
- Python 3.11+  
- Микрофон (для голоса; чат работает и без него)

### Вариант A — одной командой (рекомендуется)

Открой PowerShell в папке проекта:

```powershell
cd C:\Users\user\Desktop\friday
npm run install:all
npm run dev
```

`npm run dev` поднимает backend и Electron-окно.

### Вариант B — двумя терминалами

**Терминал 1 — backend:**

```powershell
cd C:\Users\user\Desktop\friday\apps\backend
python main.py
```

Должно появиться что-то вроде: `Uvicorn running on http://127.0.0.1:8765`.

**Терминал 2 — desktop:**

```powershell
cd C:\Users\user\Desktop\friday\apps\desktop
npm run electron:dev
```

### Проверка

1. После splash в чате справа напиши: `привет`
2. FRIDAY должна ответить через Gemini
3. Попробуй: `открой notepad` или `установи громкость на 30`

Проверка backend без UI:

```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8765/health').read())"
```

Ожидается: `{"status":"ok","service":"friday"}`

### Автозапуск при включении ПК (опционально)

```powershell
cd C:\Users\user\Desktop\friday
npm run autostart:install
```

Убрать:

```powershell
npm run autostart:remove
```

### Сборка .exe (позже)

```powershell
cd C:\Users\user\Desktop\friday\apps\desktop
npm run electron:build
```

Готовый установщик появится в `apps/desktop/release/`.

---

## Возможные проблемы

| Симптом | Что сделать |
|---------|-------------|
| Чат пишет ошибку про API key | Перезапусти backend после изменения `.env`; проверь провайдер = google |
| Окно не видит backend | Сначала запусти `python main.py`, потом desktop |
| Wake word не срабатывает | Используй текстовый чат; в Settings можно выключить wake word |
| Whisper медленный | В Settings поставь STT model = `tiny` |
| Порт 8765 занят / WinError 10048 | `npm run free-port`, затем снова `npm run dev` |
| Окно Connection Failed / ERR_CONNECTION_REFUSED | Vite или backend ещё не поднялись — закрой окна и запусти заново `npm run dev` |

---

## Безопасность

- Файл `.env` в `.gitignore` — **не коммить** ключи в git.
- Ключ ты показал в чате/скриншоте. Если репозиторий когда-нибудь станет публичным — **перевыпусти ключ** в [Google AI Studio](https://aistudio.google.com/apikey) и обнови `.env`.
- Опасные команды (`shutdown` / `restart`) требуют подтверждения в UI.

---

## Что дальше (не в текущем MVP)

Долгая память, плагины, календарь/почта, умный дом, vision («что на экране?»). Архитектура к этому готова: новые tools добавляются в `tools/registry.py`, UI уже умеет статусы и стриминг.
