import { HudSnapshot } from "../hooks/useHudStats";

interface PcSchematicProps {
  hardware: HudSnapshot["hardware"];
  cpuPercent: number;
  ramPercent: number;
}

export function PcSchematic({ hardware, cpuPercent, ramPercent }: PcSchematicProps) {
  return (
    <div className="pc-schematic">
      <svg viewBox="0 0 420 520" className="pc-svg" aria-label="PC schematic">
        <rect x="28" y="18" width="364" height="484" rx="6" className="pc-case" />
        <rect x="44" y="36" width="332" height="448" rx="3" className="pc-inner" />
        <text x="210" y="58" textAnchor="middle" className="pc-case-label">
          SYSTEM CHASSIS
        </text>

        <g className={cpuPercent > 80 ? "pc-block hot" : "pc-block"}>
          <rect x="64" y="78" width="148" height="88" rx="2" />
          <text x="138" y="108" textAnchor="middle" className="pc-tag">
            CPU
          </text>
          <text x="138" y="132" textAnchor="middle" className="pc-name">
            {clip(hardware.cpu, 22)}
          </text>
          <text x="138" y="150" textAnchor="middle" className="pc-val">
            {cpuPercent.toFixed(0)}%
          </text>
        </g>

        <g className={ramPercent > 85 ? "pc-block hot" : "pc-block"}>
          <rect x="228" y="78" width="128" height="88" rx="2" />
          <text x="292" y="108" textAnchor="middle" className="pc-tag">
            RAM
          </text>
          <text x="292" y="132" textAnchor="middle" className="pc-name">
            {clip(hardware.ram, 16)}
          </text>
          <text x="292" y="150" textAnchor="middle" className="pc-val">
            {ramPercent.toFixed(0)}%
          </text>
        </g>

        <g className="pc-block gpu">
          <rect x="64" y="186" width="292" height="100" rx="2" />
          <text x="210" y="222" textAnchor="middle" className="pc-tag">
            GPU
          </text>
          <text x="210" y="250" textAnchor="middle" className="pc-name">
            {clip(hardware.gpu, 34)}
          </text>
        </g>

        <g className="pc-block">
          <rect x="64" y="306" width="176" height="72" rx="2" />
          <text x="152" y="336" textAnchor="middle" className="pc-tag">
            STORAGE
          </text>
          <text x="152" y="358" textAnchor="middle" className="pc-name">
            {clip(hardware.disk, 24)}
          </text>
        </g>

        <g className="pc-block">
          <rect x="256" y="306" width="100" height="72" rx="2" />
          <text x="306" y="336" textAnchor="middle" className="pc-tag">
            PSU
          </text>
          <text x="306" y="358" textAnchor="middle" className="pc-name">
            ONLINE
          </text>
        </g>

        <g className="pc-block">
          <rect x="64" y="396" width="292" height="64" rx="2" />
          <text x="210" y="422" textAnchor="middle" className="pc-tag">
            MOBO
          </text>
          <text x="210" y="444" textAnchor="middle" className="pc-name">
            {clip(hardware.board, 32)}
          </text>
        </g>
      </svg>
    </div>
  );
}

function clip(s: string, n: number) {
  const t = (s || "").trim();
  return t.length > n ? `${t.slice(0, n - 1)}…` : t || "—";
}
