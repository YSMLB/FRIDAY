import { useEffect, useMemo, useState } from "react";
import { HudSnapshot } from "../hooks/useHudStats";
import { DnaHelix } from "./DnaHelix";
import { SuitSchematic } from "./SuitSchematic";

interface HudWidgetsProps {
  hud: HudSnapshot;
  status: string;
}

export function HudWidgets({ hud, status }: HudWidgetsProps) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const days = useMemo(() => calendarGrid(now), [now]);

  return (
    <aside className="hud-right">
      <div className="wid-cal">
        <div className="wid-cal-head">
          {now.toLocaleString("en-US", { month: "long", year: "numeric" }).toUpperCase()}
        </div>
        <div className="wid-cal-grid">
          {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
            <span key={`h${i}`} className="dow">
              {d}
            </span>
          ))}
          {days.map((d, i) => (
            <span key={i} className={d.today ? "today" : d.inMonth ? "" : "mute"}>
              {d.n}
            </span>
          ))}
        </div>
      </div>

      <div className="dna-wrap" aria-hidden>
        <DnaHelix />
        <SuitSchematic />
      </div>

      <div className="wid-meter">
        <div className="wid-meter-row">
          <span>CPU</span>
          <span>{hud.cpuPercent.toFixed(0)}%</span>
        </div>
        <div className="wid-bar">
          <i style={{ width: `${Math.min(100, hud.cpuPercent)}%` }} />
        </div>
        <div className="wid-meter-row">
          <span>RAM</span>
          <span>{hud.ramPercent.toFixed(0)}%</span>
        </div>
        <div className="wid-bar">
          <i style={{ width: `${Math.min(100, hud.ramPercent)}%` }} />
        </div>
      </div>

      <div className={`wid-radar status-${status}`}>
        <div className="radar-ring" />
        <div className="radar-sweep" />
        <div className="radar-core" />
      </div>
    </aside>
  );
}

function calendarGrid(now: Date) {
  const y = now.getFullYear();
  const m = now.getMonth();
  const first = new Date(y, m, 1).getDay();
  const dim = new Date(y, m + 1, 0).getDate();
  const prevDim = new Date(y, m, 0).getDate();
  const cells: { n: number; inMonth: boolean; today: boolean }[] = [];
  for (let i = 0; i < first; i++) {
    cells.push({ n: prevDim - first + i + 1, inMonth: false, today: false });
  }
  for (let d = 1; d <= dim; d++) {
    cells.push({ n: d, inMonth: true, today: d === now.getDate() });
  }
  while (cells.length % 7) {
    cells.push({ n: cells.length - first - dim + 1, inMonth: false, today: false });
  }
  return cells;
}
