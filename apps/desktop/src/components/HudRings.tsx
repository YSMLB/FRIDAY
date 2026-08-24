interface HudRingsProps {
  status: string;
}

export function HudRings({ status }: HudRingsProps) {
  const mode = ["idle", "listening", "thinking", "speaking", "error"].includes(status)
    ? status
    : "idle";

  return (
    <div className={`hud-rings status-${mode}`} aria-label={`FRIDAY status ${mode}`}>
      <div className="ring ring-4" />
      <div className="ring ring-3" />
      <div className="ring ring-2" />
      <div className="ring ring-1" />
      <div className="ring-tick" />
      <div className="core">
        <span className="core-label">FRIDAY</span>
        <span className="core-sub">J.A.R.V.I.S.</span>
      </div>
    </div>
  );
}
