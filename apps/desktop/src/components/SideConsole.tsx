import { HudSnapshot } from "../hooks/useHudStats";
import { WorldMap } from "./WorldMap";

interface SideConsoleProps {
  hud: HudSnapshot;
  dateLabel: string;
  status: string;
}

export function SideConsole({ hud, dateLabel, status }: SideConsoleProps) {
  return (
    <aside className="side-console">
      <div className="console-block">
        <div className="console-label">DATE</div>
        <div className="console-date">{dateLabel}</div>
      </div>

      <div className="console-block">
        <div className="console-label">SYSTEM LOAD</div>
        <div className="meter-row">
          <span>CPU</span>
          <strong>{hud.cpuPercent.toFixed(0)}%</strong>
        </div>
        <div className="meter-bar">
          <i style={{ width: `${Math.min(100, hud.cpuPercent)}%` }} />
        </div>
        <div className="meter-row">
          <span>RAM</span>
          <strong>{hud.ramPercent.toFixed(0)}%</strong>
        </div>
        <div className="meter-bar">
          <i style={{ width: `${Math.min(100, hud.ramPercent)}%` }} />
        </div>
        <div className="meter-sub">{hud.ramUsed || hud.hardware.cpu}</div>
      </div>

      <div className="console-block">
        <div className="console-label">NETWORK</div>
        <div className="net-lines">
          <span>↓ {hud.downloadKBs.toFixed(1)} KB/s</span>
          <span>↑ {hud.uploadKBs.toFixed(1)} KB/s</span>
        </div>
      </div>

      <div className="console-block map-block">
        <div className="console-label">WORLD</div>
        <WorldMap />
        <div className={`status-chip status-${status}`}>{status}</div>
      </div>
    </aside>
  );
}
