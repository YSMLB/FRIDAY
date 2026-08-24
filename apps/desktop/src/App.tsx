import { useEffect, useState } from "react";
import { useFridayWS } from "./hooks/useFridayWS";
import { useHudStats } from "./hooks/useHudStats";
import { SplashScreen } from "./components/SplashScreen";
import { SettingsPanel } from "./components/SettingsPanel";
import { CornerPanels } from "./components/CornerPanels";
import { FridayCore } from "./components/FridayCore";
import { CommandDock } from "./components/CommandDock";

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
    quitFriday,
  } = useFridayWS();
  const hud = useHudStats();

  const [showSplash, setShowSplash] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [splashDone, setSplashDone] = useState(false);
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
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "q") {
        e.preventDefault();
        quitFriday();
      }
    };
    window.addEventListener("keydown", onKey);
    const id = window.setInterval(() => {
      setClock(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }));
    }, 1000);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearInterval(id);
    };
  }, [quitFriday]);

  const lastLine = streaming || messages[messages.length - 1]?.content || "";

  return (
    <div className="app influx">
      {showSplash && (
        <SplashScreen
          visible={!splashDone}
          durationMs={config.splashDurationMs || 2500}
          onDone={handleSplashDone}
        />
      )}

      <main className="influx-stage">
        <FridayCore status={status} line={lastLine} />
      </main>

      <header className="influx-top">
        <span className="clock">{clock}</span>
        <span className="brand">FRIDAY</span>
        <div className="top-stats">
          <span>CPU {hud.cpuPercent.toFixed(0)}%</span>
          <span>RAM {hud.ramPercent.toFixed(0)}%</span>
          <i className={connected ? "live" : "down"} />
        </div>
      </header>

      <CommandDock
        connected={connected}
        onSubmit={sendChat}
        onOpenApp={openApp}
        onQuit={quitFriday}
        onSettings={() => setShowSettings(true)}
        browsers={hud.browsers}
      />

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
