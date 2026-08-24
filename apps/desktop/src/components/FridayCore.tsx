interface FridayCoreProps {
  status: string;
  line: string;
}

const STATUS_COPY: Record<string, string> = {
  idle: "Ready when you are",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
  error: "Signal lost",
};

export function FridayCore({ status, line }: FridayCoreProps) {
  const copy = STATUS_COPY[status] || STATUS_COPY.idle;

  return (
    <div className={`friday-core status-${status}`}>
      <video
        className="friday-core-video"
        src="./friday-core.mp4"
        autoPlay
        muted
        loop
        playsInline
        aria-hidden
      />
      <div className="friday-core-veil" />
      <div className="friday-core-copy">
        <p className="friday-kicker">FRIDAY</p>
        <h1>{copy}</h1>
        {line ? <p className="friday-line">{line}</p> : null}
      </div>
    </div>
  );
}
