export function SuitSchematic() {
  return (
    <div className="suit-pair" aria-hidden>
      <svg className="suit-svg" viewBox="0 0 40 80">
        <ellipse cx="20" cy="10" rx="6" ry="7" fill="none" stroke="#3ad6e8" />
        <path d="M14 18 L10 28 L12 48 L16 72 L24 72 L28 48 L30 28 L26 18" fill="none" stroke="#3ad6e8" />
        <circle cx="20" cy="26" r="3" fill="none" stroke="#7ef4ff" />
        <path d="M10 28 L4 40 M30 28 L36 40" fill="none" stroke="#3ad6e8" />
        <path d="M16 72 L14 80 M24 72 L26 80" fill="none" stroke="#3ad6e8" />
      </svg>
      <svg className="suit-svg side" viewBox="0 0 28 80">
        <ellipse cx="16" cy="10" rx="4" ry="7" fill="none" stroke="#3ad6e8" />
        <path d="M16 17 L14 28 L18 48 L16 72 L20 72 L22 48 L20 28" fill="none" stroke="#3ad6e8" />
        <circle cx="18" cy="26" r="2" fill="none" stroke="#7ef4ff" />
        <path d="M14 28 L6 36" fill="none" stroke="#3ad6e8" />
      </svg>
    </div>
  );
}
