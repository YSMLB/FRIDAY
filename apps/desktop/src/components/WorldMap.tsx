export function WorldMap() {
  return (
    <svg className="world-map" viewBox="0 0 240 110" aria-hidden>
      <path
        d="M18 48 C28 30 42 22 62 28 C74 16 96 14 112 26 C128 12 150 18 168 32 C186 22 208 28 226 44 C210 62 186 70 164 62 C142 78 118 80 94 68 C70 78 44 72 28 60 C20 58 16 54 18 48Z"
        fill="none"
        stroke="rgba(58,214,232,0.35)"
        strokeWidth="1"
      />
      <path d="M34 46 C48 34 70 36 78 48 C66 54 44 54 34 46Z" fill="none" stroke="rgba(58,214,232,0.7)" />
      <path d="M86 42 C104 30 128 34 136 48 C118 56 96 54 86 42Z" fill="none" stroke="rgba(58,214,232,0.7)" />
      <path d="M148 40 C168 32 188 38 196 50 C178 58 156 52 148 40Z" fill="none" stroke="rgba(58,214,232,0.65)" />
      <path d="M70 62 C86 58 96 68 90 78 C78 80 68 72 70 62Z" fill="none" stroke="rgba(58,214,232,0.5)" />
      <circle cx="58" cy="44" r="1.4" fill="#3ad6e8" />
      <circle cx="118" cy="40" r="1.4" fill="#3ad6e8" />
      <circle cx="174" cy="46" r="1.4" fill="#3ad6e8" />
    </svg>
  );
}
