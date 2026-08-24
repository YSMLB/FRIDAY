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
  onOpenApp,
  onQuit,
  onSettings,
  browsers,
}: CommandDockProps) {
  const [text, setText] = useState("");
  const [appsOpen, setAppsOpen] = useState(false);

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
        <button type="button" className="pill solid" onClick={() => setAppsOpen((v) => !v)}>
          Open apps
        </button>
        <button type="button" className="pill ghost accent" onClick={onQuit}>
          Stop Friday
        </button>
      </div>
      {appsOpen ? (
        <div className="pill-row nested">
          {(browsers.length ? browsers : ["edge", "chrome", "firefox"]).map((b) => (
            <button key={b} type="button" className="pill ghost" onClick={() => onOpenApp(b)}>
              {b}
            </button>
          ))}
          <button type="button" className="pill ghost" onClick={() => onOpenApp("steam")}>
            steam
          </button>
          <button type="button" className="pill ghost" onClick={() => onOpenApp("discord")}>
            discord
          </button>
          <button type="button" className="pill ghost" onClick={() => onOpenApp("cursor")}>
            cursor
          </button>
          <button type="button" className="pill ghost" onClick={onSettings}>
            config
          </button>
        </div>
      ) : null}
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
