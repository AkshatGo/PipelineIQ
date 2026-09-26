import { useEffect, useState } from 'react';

type HealedCounterProps = { reducedMotion: boolean };

export function HealedCounter({ reducedMotion }: HealedCounterProps) {
  const [count, setCount] = useState(1284093);

  useEffect(() => {
    if (reducedMotion) return;
    const id = window.setInterval(() => {
      setCount((c) => c + 1 + Math.floor(Math.random() * 3));
    }, 2600);
    return () => window.clearInterval(id);
  }, [reducedMotion]);

  return (
    <dl className="mt-14 flex flex-wrap items-end gap-x-12 gap-y-6 border-t border-line pt-6">
      <div>
        <dt className="flex items-center gap-2 text-[15px] text-muted">
          <span className="h-2 w-2 rounded-full bg-fix" aria-hidden="true" />
          Builds healed so far
        </dt>
        <dd className="mt-1 font-mono text-[40px] font-medium leading-none tabular-nums text-paper" aria-live="off">
          {count.toLocaleString('en-US')}
        </dd>
      </div>
      <div>
        <dt className="text-[15px] text-muted">Median fix time</dt>
        <dd className="mt-1 font-mono text-[28px] font-medium leading-none text-paper">
          41<span className="text-lg text-muted">s</span>
        </dd>
      </div>
      <div>
        <dt className="text-[15px] text-muted">PRs merged unedited</dt>
        <dd className="mt-1 font-mono text-[28px] font-medium leading-none text-paper">
          87<span className="text-lg text-muted">%</span>
        </dd>
      </div>
    </dl>
  );
}