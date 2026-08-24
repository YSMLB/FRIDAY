import { useState, useRef, useEffect } from "react";
import { ChatEntry } from "../hooks/useFridayWS";

interface ChatPanelProps {
  messages: ChatEntry[];
  streaming: string;
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatPanel({ messages, streaming, onSend, disabled }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const recent = messages.slice(-8);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span>COMMS</span>
        <span className="hint">VOICE PRIMARY</span>
      </div>
      <div className="chat-messages">
        {recent.map((m, i) => (
          <div key={`${i}-${m.role}`} className={`chat-msg chat-msg-${m.role}`}>
            <span className="chat-role">
              {m.role === "user" ? "YOU" : m.role === "assistant" ? "FRIDAY" : "SYS"}
            </span>
            <span className="chat-text">{m.content}</span>
          </div>
        ))}
        {streaming && (
          <div className="chat-msg chat-msg-assistant streaming">
            <span className="chat-role">FRIDAY</span>
            <span className="chat-text">
              {streaming}
              <span className="cursor">|</span>
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type if needed…"
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !input.trim()}>
          SEND
        </button>
      </form>
    </div>
  );
}
