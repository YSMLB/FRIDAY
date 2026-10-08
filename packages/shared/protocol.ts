export type FridayStatus = "idle" | "listening" | "thinking" | "speaking" | "error";

export type LLMProvider = "openai" | "anthropic" | "google" | "qwen" | "ollama";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface FridayConfig {
  llmProvider: LLMProvider;
  llmModel: string;
  llmBaseUrl: string;
  wakeWordEnabled: boolean;
  wakeWord: string;
  ttsVoice: string;
  sttModel: string;
  autostart: boolean;
  splashDurationMs: number;
  hasQwenKey?: boolean;
  ollamaReady?: boolean;
}

export type WSClientMessage =
  | { type: "chat"; content: string }
  | { type: "get_config" }
  | { type: "update_config"; config: Partial<FridayConfig> }
  | { type: "get_status" }
  | { type: "voice_toggle"; enabled: boolean }
  | { type: "voice_playback_done" }
  | { type: "open_app"; name: string }
  | { type: "web_open"; url: string }
  | { type: "confirm_action"; actionId: string; confirmed: boolean }
  | { type: "quit_app" };

export type WSServerMessage =
  | { type: "status"; status: FridayStatus }
  | { type: "chat_delta"; content: string }
  | { type: "chat_done"; content: string }
  | { type: "chat_error"; error: string }
  | { type: "config"; config: FridayConfig }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "confirm_request"; actionId: string; message: string }
  | { type: "voice_transcript"; text: string }
  | { type: "audio_ready"; path: string }
  | { type: "mic_info"; mic: Record<string, unknown> }
  | { type: "wake_ack" }
  | { type: "app_quit" };

export const DEFAULT_CONFIG: FridayConfig = {
  llmProvider: "ollama",
  llmModel: "qwen2.5:3b",
  llmBaseUrl: "http://127.0.0.1:11434/v1",
  wakeWordEnabled: true,
  wakeWord: "пятница",
  ttsVoice: "ru-RU-SvetlanaNeural",
  sttModel: "tiny",
  autostart: true,
  splashDurationMs: 2500,
  hasQwenKey: false,
  ollamaReady: true,
};

export const BACKEND_WS_URL = "ws://127.0.0.1:8765/ws";
export const BACKEND_HTTP_URL = "http://127.0.0.1:8765";
