import { FormEvent, useEffect, useState } from "react";
import { useFridayWS } from "./hooks/useFridayWS";
import { useHudStats } from "./hooks/useHudStats";
import { HudRings } from "./components/HudRings";
import { SplashScreen } from "./components/SplashScreen";
import { SettingsPanel } from "./components/SettingsPanel";
import { CornerPanels } from "./components/CornerPanels";
import { LauncherRail } from "./components/LauncherRail";
import { HardwareStage } from "./components/HardwareStage";
import { HudWidgets } from "./components/HudWidgets";
import { WorldMap } from "./components/WorldMap";

export default function App() {
  const {
    connected,
    status,
    config,
    messages,
    streaming,
    confirmRequest,
    cornerPanels,
    dismissCorner,
    sendChat,
    updateConfig,
    confirmAction,
    toggleVoice,
    openApp,
    openWeb,
  } = useFridayWS();
  const hud = useHudStats();

  const [showSplash, setShowSplash] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [splashDone, setSplashDone] = useState(false);
  const [query, setQuery] = useState("");
  const [clock, setClock] = useState(() =>
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
  );

  const handleSplashDone = () => {
    setSplashDone(true);
    setTimeout(() => setShowSplash(false), 400);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") window.friday?.hide?.();
    };
    window.addEventListener("keydown", onKey);
    const id = window.setInterval(() => {
      setClock(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }));
    }, 1000);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearInterval(id);
    };
  }, []);

  const lastLine = streaming || messages[messages.length - 1]?.content || "";
  const bat = hud.battery?.percent ?? 100;

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    openWeb(`https://www.google.com/search?q=${encodeURIComponent(q)}`);
    setQuery("");
  };

  return (
    <div className="app visor">
      {showSplash && (
        <SplashScreen
          visible={!splashDone}
          durationMs={config.splashDurationMs || 2500}
          onDone={handleSplashDone}
        />
      )}

      <svg className="visor-chrome" viewBox="0 0 1600 900" preserveAspectRatio="none" aria-hidden>
        <defs>
          <linearGradient id="visorStroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(58,214,232,0.15)" />
            <stop offset="50%" stopColor="rgba(126,244,255,0.9)" />
            <stop offset="100%" stopColor="rgba(58,214,232,0.15)" />
          </linearGradient>
        </defs>
        <polygon
          points="90,6 1510,6 1594,78 1594,822 1510,894 90,894 6,822 6,78"
          fill="none"
          stroke="url(#visorStroke)"
          strokeWidth="2.2"
        />
        <polygon
          points="120,28 1480,28 1568,92 1568,808 1480,872 120,872 32,808 32,92"
          fill="none"
          stroke="rgba(58,214,232,0.22)"
          strokeWidth="1"
        />
        <path d="M40,110 L90,40 L240,40" fill="none" stroke="rgba(58,214,232,0.85)" strokeWidth="2" />
        <path d="M1560,110 L1510,40 L1360,40" fill="none" stroke="rgba(58,214,232,0.85)" strokeWidth="2" />
        <path d="M40,790 L90,860 L240,860" fill="none" stroke="rgba(58,214,232,0.85)" strokeWidth="2" />
        <path d="M1560,790 L1510,860 L1360,860" fill="none" stroke="rgba(58,214,232,0.85)" strokeWidth="2" />
        <path d="M70,40 L70,18 L200,18" fill="none" stroke="rgba(58,214,232,0.45)" />
        <path d="M1530,40 L1530,18 L1400,18" fill="none" stroke="rgba(58,214,232,0.45)" />
        <polygon points="740,858 800,808 860,858 800,892" fill="rgba(0,20,28,0.7)" stroke="rgba(58,214,232,0.9)" strokeWidth="1.6" />
        <polygon points="770,858 800,828 830,858 800,874" fill="none" stroke="rgba(126,244,255,0.8)" />
      </svg>

      <div className="hud-top">
        <div className="battery-gauge" title="Battery">
          <svg viewBox="0 0 120 70">
            <path d="M10,60 A50,50 0 0 1 110,60" fill="none" stroke="rgba(58,214,232,0.25)" strokeWidth="8" />
            <path
              d="M10,60 A50,50 0 0 1 110,60"
              fill="none"
              stroke="#3ad6e8"
              strokeWidth="8"
              strokeDasharray={`${(bat / 100) * 157} 157`}
            />
            <text x="60" y="52" textAnchor="middle">
              BATTERY
            </text>
          </svg>
        </div>
        <div className="top-clock">{clock}</div>
        <div className="top-right">
          <button type="button" className="gear-btn" onClick={() => setShowSettings(true)}>
            ⚙
          </button>
          <div className="fan-ornament">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>

      <main className="main-hud">
        <div className="hud-left">
          <LauncherRail browsers={hud.browsers} onOpenApp={openApp} />
          <div className="search-cluster">
            <form className="google-box" onSubmit={onSearch}>
              <span className="g-ico">⌕</span>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Google" />
            </form>
            <div className="net-readout">
              DOWNLOAD: {hud.downloadKBs.toFixed(1)} KB/S
              <br />
              UPLOAD: {hud.uploadKBs.toFixed(1)} KB/S
            </div>
          </div>
          <div className="jarvis-core-wrap">
            <HudRings status={status} />
            <WorldMap />
          </div>
        </div>

        <div className="hud-center">
          <HardwareStage
            status={status}
            labels={{
              cpu: hud.hardware.cpu,
              gpu: hud.hardware.gpu,
              ram: hud.hardware.ram,
              disk: hud.hardware.disk,
            }}
          />
          <div className="voice-line">
            {connected ? (lastLine || "AWAITING VOICE // FRIDAY") : "OFFLINE"}
          </div>
          <form
            className="hidden-chat"
            onSubmit={(e) => {
              e.preventDefault();
              const t = query.trim();
              if (t) sendChat(t);
            }}
          />
        </div>

        <HudWidgets hud={hud} status={status} />
      </main>

      <CornerPanels items={cornerPanels} onDismiss={dismissCorner} />

      {confirmRequest && (
        <div className="confirm-overlay">
          <div className="confirm-box">
            <p>{confirmRequest.message}</p>
            <div className="confirm-actions">
              <button type="button" onClick={() => confirmAction(confirmRequest.actionId, true)}>
                CONFIRM
              </button>
              <button type="button" onClick={() => confirmAction(confirmRequest.actionId, false)}>
                ABORT
              </button>
            </div>
          </div>
        </div>
      )}

      {showSettings && (
        <SettingsPanel
          config={config}
          onSave={updateConfig}
          onClose={() => setShowSettings(false)}
          onVoiceToggle={toggleVoice}
        />
      )}
    </div>
  );
}
