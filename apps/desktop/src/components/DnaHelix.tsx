import { useRef } from "react";

export function DnaHelix() {
  const id = useRef(`dna-${Math.random().toString(36).slice(2, 8)}`).current;
  return (
    <svg className="dna-svg" viewBox="0 0 48 90" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7ef4ff" />
          <stop offset="100%" stopColor="#3ad6e8" />
        </linearGradient>
      </defs>
      {Array.from({ length: 9 }, (_, i) => {
        const y = 6 + i * 9;
        const phase = i % 2 === 0;
        const x1 = phase ? 10 : 38;
        const x2 = phase ? 38 : 10;
        return (
          <g key={i}>
            <line x1={x1} y1={y} x2={x2} y2={y} stroke={`url(#${id})`} strokeWidth="1.2" opacity="0.7" />
            <circle cx={x1} cy={y} r="2.2" fill="#3ad6e8" />
            <circle cx={x2} cy={y} r="2.2" fill="#7ef4ff" />
          </g>
        );
      })}
      <path
        d="M10 6 C38 22 10 44 38 62 C10 80 24 88 24 88"
        fill="none"
        stroke="#3ad6e8"
        strokeWidth="1.4"
      />
      <path
        d="M38 6 C10 22 38 44 10 62 C38 80 24 88 24 88"
        fill="none"
        stroke="#7ef4ff"
        strokeWidth="1.4"
      />
    </svg>
  );
}
