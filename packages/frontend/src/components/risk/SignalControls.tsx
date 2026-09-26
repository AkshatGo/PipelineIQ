import { RiskSignals } from '@/utils/risk';

type SignalControlsProps = {
  signals: RiskSignals;
  onChange: <K extends keyof RiskSignals>(key: K, value: RiskSignals[K]) => void;
};

const sliders: { key: 'linesChanged' | 'filesChanged' | 'priorFailures'; label: string; min: number; max: number; step: number }[] = [
  { key: 'linesChanged', label: 'Lines changed', min: 0, max: 1000, step: 10 },
  { key: 'filesChanged', label: 'Files changed', min: 1, max: 40, step: 1 },
  { key: 'priorFailures', label: 'Similar failures before', min: 0, max: 8, step: 1 },
];

const switches: { key: 'testsFailed' | 'sensitiveFiles' | 'hasReview'; label: string; hint: string }[] = [
  { key: 'testsFailed', label: 'Tests are failing', hint: 'Not just lint or build' },
  { key: 'sensitiveFiles', label: 'Touches sensitive files', hint: 'Auth, deploy, or dependencies' },
  { key: 'hasReview', label: 'Required review in place', hint: 'Branch protection with reviewers' },
];

export function SignalControls({ signals, onChange }: SignalControlsProps) {
  return (
    <div className="space-y-8">
      <fieldset>
        <legend className="text-[15px] font-medium text-paper">Target branch</legend>
        <div role="radiogroup" className="mt-3 grid grid-cols-2 rounded-md border border-line bg-ink p-1">
          {(['main', 'feature'] as const).map((b) => {
            const active = signals.branch === b;
            return (
              <button
                key={b}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => onChange('branch', b)}
                className={`rounded px-3 py-2 font-mono text-[13px] transition-colors duration-150 ${
                  active ? 'bg-brass text-ink' : 'text-muted hover:text-paper'
                }`}
              >
                {b === 'main' ? 'main (protected)' : 'feat/*'}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="space-y-6">
        {sliders.map((sl) => {
          const value = signals[sl.key];
          const fill = ((value - sl.min) / (sl.max - sl.min)) * 100;
          const id = `slider-${sl.key}`;
          return (
            <div key={sl.key}>
              <div className="flex items-baseline justify-between">
                <label htmlFor={id} className="text-[15px] text-paper">
                  {sl.label}
                </label>
                <span className="font-mono text-[14px] text-paper tabular-nums">{value}</span>
              </div>
              <input
                id={id}
                type="range"
                min={sl.min}
                max={sl.max}
                step={sl.step}
                value={value}
                onChange={(e) => onChange(sl.key, Number(e.target.value))}
                className="bench-range mt-3"
                style={{ '--fill': `${fill}%` } as React.CSSProperties}
              />
            </div>
          );
        })}
      </div>

      <ul className="divide-y divide-line border-y border-line">
        {switches.map((sw) => {
          const on = signals[sw.key];
          return (
            <li key={sw.key} className="flex items-center justify-between gap-4 py-3.5">
              <div>
                <p className="text-[15px] text-paper" id={`sw-${sw.key}`}>
                  {sw.label}
                </p>
                <p className="text-[13px] text-muted">{sw.hint}</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={on}
                aria-labelledby={`sw-${sw.key}`}
                onClick={() => onChange(sw.key, !on)}
                className={`relative h-6 w-11 shrink-0 rounded-md border transition-colors duration-150 ${
                  on ? 'border-brass bg-brass' : 'border-line bg-ink-700'
                }`}
              >
                <span
                  className={`absolute top-[3px] h-4 w-4 rounded-sm transition-transform duration-150 ease-out ${
                    on ? 'translate-x-[22px] bg-ink' : 'translate-x-[3px] bg-muted'
                  }`}
                />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}