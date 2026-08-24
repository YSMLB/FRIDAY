import { useState } from "react";

interface LauncherRailProps {
  browsers: string[];
  onOpenApp: (name: string) => void;
}

const BROWSER_LABEL: Record<string, string> = {
  edge: "EDGE",
  chrome: "CHROME",
  firefox: "FIREFOX",
};

export function LauncherRail({ browsers, onOpenApp }: LauncherRailProps) {
  const [safariOpen, setSafariOpen] = useState(false);

  return (
    <nav className="launcher-rail">
      <div className="launcher-stack">
        <div className="launcher-safari">
          <button
            type="button"
            className="trap-btn"
            onClick={() => setSafariOpen((v) => !v)}
          >
            SAFARI
          </button>
          {safariOpen ? (
            <div className="safari-picker">
              <div className="safari-picker-title">BROWSER</div>
              {(browsers.length ? browsers : ["edge", "chrome", "firefox"]).map((b) => (
                <button
                  key={b}
                  type="button"
                  className="safari-opt"
                  onClick={() => {
                    onOpenApp(b);
                    setSafariOpen(false);
                  }}
                >
                  {BROWSER_LABEL[b] || b.toUpperCase()}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <button type="button" className="trap-btn" onClick={() => onOpenApp("steam")}>
          STEAM
        </button>
        <button type="button" className="trap-btn" onClick={() => onOpenApp("discord")}>
          DISCORD
        </button>
        <button type="button" className="trap-btn" onClick={() => onOpenApp("cursor")}>
          CURSOR
        </button>
      </div>
    </nav>
  );
}
