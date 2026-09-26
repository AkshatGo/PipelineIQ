import { motion, useReducedMotion } from 'framer-motion';
import { APPROVAL_BELOW, AUTO_FIX_BELOW } from '@/utils/risk';

type RiskDialProps = { score: number };

const CX = 110;
const CY = 110;
const R = 88;
const START = 150;
const SWEEP = 240;

function polar(angleDeg: number, r = R) {
  const a = (angleDeg * Math.PI) / 180;
  return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) };
}

const s = polar(START);
const e = polar(START + SWEEP);
const ARC = `M ${s.x} ${s.y} A ${R} ${R} 0 1 1 ${e.x} ${e.y}`;

export function RiskDial({ score }: RiskDialProps) {
  const reduced = useReducedMotion() ?? false;
  const transition = reduced ? { duration: 0 } : { duration: 0.25, ease: [0.23, 1, 0.32, 1] };
  const needle = polar(START + (SWEEP * score) / 100);

  return (
    <svg viewBox="0 0 220 200" className="w-full" aria-hidden="true">
      <defs>
        <linearGradient id="risk-arc" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#7C9A6B" />
          <stop offset="45%" stopColor="#C98A3E" />
          <stop offset="100%" stopColor="#B3452F" />
        </linearGradient>
      </defs>
      <path d={ARC} fill="none" className="stroke-ink-700" strokeWidth="14" strokeLinecap="butt" />
      <motion.path
        d={ARC}
        fill="none"
        stroke="url(#risk-arc)"
        strokeWidth="14"
        pathLength={100}
        initial={false}
        animate={{ strokeDasharray: `${Math.max(score, 0.01)} 100` }}
        transition={transition}
      />
      {[AUTO_FIX_BELOW, APPROVAL_BELOW].map((t) => {
        const a = START + (SWEEP * t) / 100;
        const p1 = polar(a, R - 12);
        const p2 = polar(a, R + 12);
        const lbl = polar(a, R + 22);
        return (
          <g key={t}>
            <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} className="stroke-paper" strokeWidth="1.5" />
            <text x={lbl.x} y={lbl.y + 3} textAnchor="middle" className="fill-muted font-mono" fontSize="9">
              {t}
            </text>
          </g>
        );
      })}
      <motion.circle
        r="7"
        className="fill-paper stroke-ink"
        strokeWidth="3"
        initial={false}
        animate={{ cx: needle.x, cy: needle.y }}
        transition={transition}
      />
    </svg>
  );
}