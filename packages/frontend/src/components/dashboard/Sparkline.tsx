
type SparklineProps = { values: number[] };

export function Sparkline({ values }: SparklineProps) {
  const W = 320;
  const H = 72;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = 6 + (1 - (v - min) / (max - min)) * (H - 12);
    return [x, y] as const;
  });
  const [lx, ly] = pts[pts.length - 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-[72px] w-full overflow-visible" role="img" aria-label="Median time-to-green falling from 38 minutes to 41 seconds over 14 days">
      <line x1="0" x2={W} y1={H - 6} y2={H - 6} className="stroke-line" strokeDasharray="2 4" />
      <polyline
        points={pts.map(([x, y]) => `${x},${y}`).join(' ')}
        fill="none"
        className="stroke-copper"
        strokeWidth="2"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={lx} cy={ly} r="4" className="fill-fix stroke-ink-900" strokeWidth="2" />
    </svg>
  );
}