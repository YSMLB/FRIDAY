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
  const [safari, setSafari] = useState(false);

  const send = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    onSubmit(t);
    setText("");
  };

  return (
    <div className="command-dock">
      <div className="pill-row">
        <button type="button" className="pill solid" onClick={() => setSafari((v) => !v)}>
          Browsers
        </button>
        <button type="button" className="pill ghost" onClick={() => onOpenApp("steam")}>
          Steam
        </button>
        <button type="button" className="pill ghost" onClick={() => onOpenApp("discord")}>
          Discord
        </button>
        <button type="button" className="pill ghost" onClick={() => onOpenApp("cursor")}>
          Cursor
        </button>
        <button type="button" className="pill ghost" onClick={onSettings}>
          Config
        </button>
        <button type="button" className="pill danger" onClick={onQuit}>
          Stop FRIDAY
        </button>
      </div>
      {safari ? (
        <div className="pill-row nested">
          {(browsers.length ? browsers : ["edge", "chrome", "firefox"]).map((b) => (
            <button
              key={b}
              type="button"
              className="pill solid"
              onClick={() => {
                onOpenApp(b);
                setSafari(false);
              }}
            >
              {b}
            </button>
          ))}
        </div>
      ) : null}
      <form className="command-form" onSubmit={send}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={connected ? "Ask Friday to run the PC…" : "Offline"}
        />
        <button type="submit" className="pill solid" disabled={!connected}>
          Send
        </button>
      </form>
    </div>
  );
}
