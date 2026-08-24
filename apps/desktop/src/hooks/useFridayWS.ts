import { useCallback, useEffect, useRef, useState } from "react";
import {
  BACKEND_HTTP_URL,
  BACKEND_WS_URL,
  DEFAULT_CONFIG,
  FridayConfig,
  FridayStatus,
  WSServerMessage,
} from "@shared/protocol";
import type { CornerInfo, CornerSlot } from "../components/CornerPanels";

export interface ChatEntry {
  role: "user" | "assistant" | "system";
  content: string;
}

const SLOT_ORDER: CornerSlot[] = ["tr", "tl", "br", "bl"];

function formatArgs(args: Record<string, unknown>): string {
  try {
    return JSON.stringify(args, null, 0);
  } catch {
    return String(args);
  }
}

export function useFridayWS() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<FridayStatus>("idle");
  const [config, setConfig] = useState<FridayConfig>(DEFAULT_CONFIG);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [streaming, setStreaming] = useState("");
  const [confirmRequest, setConfirmRequest] = useState<{ actionId: string; message: string } | null>(null);
  const [cornerPanels, setCornerPanels] = useState<CornerInfo[]>([]);
  const [micInfo, setMicInfo] = useState<Record<string, unknown> | null>(null);
  const streamBuffer = useRef("");
  const slotIndex = useRef(0);
  const audioEl = useRef<HTMLAudioElement>(typeof Audio === "undefined" ? (null as unknown as HTMLAudioElement) : new Audio());

  const pushCorner = useCallback((title: string, body: string, meta?: string) => {
    const slot = SLOT_ORDER[slotIndex.current % SLOT_ORDER.length];
    slotIndex.current += 1;
    const id = `${Date.now()}-${slotIndex.current}`;
    setCornerPanels((prev) => {
      const next = [...prev.filter((p) => p.slot !== slot), { id, slot, title, body, meta }];
      return next.slice(-4);
    });
    window.setTimeout(() => {
      setCornerPanels((prev) => prev.filter((p) => p.id !== id));
    }, 12000);
  }, []);

  const dismissCorner = useCallback((id: string) => {
    setCornerPanels((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(BACKEND_WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 2000);
    };

    ws.onmessage = (event) => {
      const msg: WSServerMessage = JSON.parse(event.data);

      switch (msg.type) {
        case "status":
          setStatus(msg.status);
          break;
        case "config":
          setConfig(msg.config);
          break;
        case "chat_delta":
          streamBuffer.current += msg.content;
          setStreaming(streamBuffer.current);
          break;
        case "chat_done": {
          const content = msg.content || streamBuffer.current;
          setMessages((prev) => [...prev, { role: "assistant", content }]);
          if (content.trim()) {
            const preview = content.length > 160 ? `${content.slice(0, 157)}…` : content;
            pushCorner("RESPONSE", preview, "CHANNEL // ASSISTANT");
          }
          streamBuffer.current = "";
          setStreaming("");
          break;
        }
        case "chat_error":
          setMessages((prev) => [...prev, { role: "system", content: `Error: ${msg.error}` }]);
          pushCorner("FAULT", msg.error, "SYSTEM");
          streamBuffer.current = "";
          setStreaming("");
          break;
        case "tool_call":
          pushCorner(
            `TOOL // ${msg.name.toUpperCase()}`,
            formatArgs(msg.args),
            "OPERATOR ACTION"
          );
          break;
        case "voice_transcript":
          setMessages((prev) => [...prev, { role: "user", content: msg.text }]);
          pushCorner("VOICE IN", msg.text, "MICROPHONE");
          break;
        case "confirm_request":
          setConfirmRequest({ actionId: msg.actionId, message: msg.message });
          break;
        case "audio_ready": {
          const name = msg.path.split(/[/\\]/).pop() || "";
          const url = `${BACKEND_HTTP_URL}/audio/${encodeURIComponent(name)}`;
          const el = audioEl.current;
          if (!el) {
            send({ type: "voice_playback_done" });
            break;
          }
          el.pause();
          el.onended = () => send({ type: "voice_playback_done" });
          el.onerror = () => send({ type: "voice_playback_done" });
          void fetch(url)
            .then((r) => r.blob())
            .then((blob) => {
              if (el.dataset.blob) URL.revokeObjectURL(el.dataset.blob);
              const src = URL.createObjectURL(blob);
              el.dataset.blob = src;
              el.src = src;
              return el.play();
            })
            .catch(() => send({ type: "voice_playback_done" }));
          break;
        }
        case "mic_info":
          setMicInfo(msg.mic);
          pushCorner(
            "MIC",
            String(msg.mic?.name || "unknown"),
            `GATE ${(Number(msg.mic?.speechRms) || 0).toFixed(4)}`
          );
          break;
        case "wake_ack":
          pushCorner("WAKE", "Слушаю", "SESSION");
          break;
      }
    };
  }, [pushCorner, send]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  const sendChat = useCallback(
    (content: string) => {
      if (!content.trim()) return;
      setMessages((prev) => [...prev, { role: "user", content }]);
      streamBuffer.current = "";
      setStreaming("");
      send({ type: "chat", content });
    },
    [send]
  );

  const updateConfig = useCallback(
    (partial: Partial<FridayConfig>) => {
      send({ type: "update_config", config: partial });
    },
    [send]
  );

  const confirmAction = useCallback(
    (actionId: string, confirmed: boolean) => {
      send({ type: "confirm_action", actionId, confirmed });
      setConfirmRequest(null);
    },
    [send]
  );

  const toggleVoice = useCallback(
    (enabled: boolean) => {
      send({ type: "voice_toggle", enabled });
    },
    [send]
  );

  const openApp = useCallback(
    (name: string) => {
      send({ type: "open_app", name });
    },
    [send]
  );

  const openWeb = useCallback(
    (url: string) => {
      send({ type: "web_open", url });
    },
    [send]
  );

  return {
    connected,
    status,
    config,
    messages,
    streaming,
    confirmRequest,
    cornerPanels,
    micInfo,
    dismissCorner,
    sendChat,
    updateConfig,
    confirmAction,
    toggleVoice,
    openApp,
    openWeb,
  };
}
