interface SplashScreenProps {
  visible: boolean;
  durationMs: number;
  onDone: () => void;
}

export function SplashScreen({ visible, durationMs, onDone }: SplashScreenProps) {
  if (!visible) return null;

  return (
    <div
      className="splash"
      style={{ animationDuration: `${durationMs}ms` }}
      onAnimationEnd={onDone}
      onClick={() => {
        const a = new Audio(
          "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="
        );
        void a.play().catch(() => undefined);
        onDone();
      }}
    >
      <div className="splash-grid" />
      <div className="splash-content">
        <div className="splash-rings">
          <div className="ring ring-1" />
          <div className="ring ring-2" />
          <div className="ring ring-3" />
        </div>
        <h1 className="splash-title">FRIDAY</h1>
        <p className="splash-status">SYSTEM ONLINE</p>
        <div className="splash-loader">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}
