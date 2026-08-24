import { FormEvent, useState } from "react";

interface CommandDockProps {
  connected: boolean;
  onSubmit: (text: string) => void;
  onOpenApp: (name: string) => void;
  onQuit: () => void;
  onSettings: () => void;
  browsers: string[];
}

export function CommandDock({
  connected,
  onSubmit,
  onQuit,
  onSettings,
}: CommandDockProps) {
  const [text, setText] = useState("");

  const send = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    onSubmit(t);
    setText("");
  };

  return (
    <div className="command-dock">
      <div className="pill-row primary">
        <button type="button" className="pill solid" onClick={onSettings}>
          Config
        </button>
        <button type="button" className="pill ghost accent" onClick={onQuit}>
          Stop Friday
        </button>
      </div>
      <form className="command-form" onSubmit={send}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={connected ? "Tell Friday what to do" : "Offline"}
        />
        <button type="submit" className="pill solid" disabled={!connected}>
          Send
        </button>
      </form>
    </div>
  );
}
