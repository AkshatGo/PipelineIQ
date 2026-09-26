import { useMemo, useState } from 'react';
import { assessRisk, riskTextClass, RiskAction, RiskSignals } from '@/utils/risk';
import { RiskDial } from './RiskDial';
import { SignalControls } from './SignalControls';

const actionCopy: Record<RiskAction, { title: string; detail: string }> = {
  auto_fix: {
    title: 'Opens a pull request on its own',
    detail: 'Under 30. The patch branch is pushed, CI re-runs, and the PR opens.',
  },
  approval: {
    title: 'Asks in Slack first',
    detail: '30 to 59. The fix is posted to your channel and waits for a human.',
  },
  block: {
    title: 'Blocks the fix',
    detail: '60 or more. The failure is flagged and assigned; no branch is pushed.',
  },
};

export function RiskLab() {
  const [signals, setSignals] = useState<RiskSignals>({
    branch: 'main',
    linesChanged: 120,
    filesChanged: 4,
    testsFailed: true,
    sensitiveFiles: false,
    hasReview: true,
    priorFailures: 1,
  });

  const result = useMemo(() => assessRisk(signals), [signals]);
  const copy = actionCopy[result.action];

  const handleChange = <K extends keyof RiskSignals>(key: K, value: RiskSignals[K]) => {
    setSignals((s) => ({ ...s, [key]: value }));
  };

  return (
    <section id="risk-lab" className="border-b border-line bg-ink-900 py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="max-w-2xl">
          <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
            Try the risk score yourself
          </h2>
          <p className="mt-6 max-w-[58ch] text-lg leading-relaxed text-muted">
            It's the same deterministic scorer PipelineIQ runs on every fix: seven signals, fixed weights,
            no model guessing. Change a signal and watch the decision move.
          </p>
        </div>

        <div className="mt-14 grid gap-12 lg:grid-cols-[360px_minmax(0,1fr)] lg:gap-16">
          <SignalControls signals={signals} onChange={handleChange} />

          <div className="grid gap-10 rounded-lg border border-line bg-ink p-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:p-8">
            <div className="grid gap-10">
              <div className="relative mx-auto w-full max-w-[320px]">
                <RiskDial score={result.score} />
                <div className="absolute inset-x-0 top-[38%] text-center" aria-live="polite">
                  <p className={`font-mono text-[64px] font-medium leading-none tabular-nums ${riskTextClass(result.score)}`}>
                    {result.score}
                  </p>
                  <p className="mt-1 font-mono text-[13px] text-muted">
                    of 100 · {result.band} risk
                  </p>
                </div>
              </div>
              <div className="mt-4 border-t border-line pt-5">
                <p className="text-xl font-semibold text-paper">{copy.title}</p>
                <p className="mt-1.5 text-[15px] leading-relaxed text-muted">{copy.detail}</p>
              </div>
            </div>

            <div>
              <h3 className="text-[15px] font-medium text-paper">Where the points come from</h3>
              <ul className="mt-4 space-y-4">
                {result.factors.map((f) => {
                  const active = f.points > 0;
                  return (
                    <li key={f.key}>
                      <div className="flex items-baseline justify-between gap-3">
                        <span className={`font-mono text-[13px] ${active ? 'text-paper' : 'text-muted'}`}>{f.key}</span>
                        <span className={`font-mono text-[13px] tabular-nums ${active ? 'text-copper' : 'text-muted'}`}>
                          +{f.points}
                        </span>
                      </div>
                      <div className="mt-1.5 h-1 rounded-sm bg-ink-700">
                        <div
                          className="h-1 rounded-sm bg-copper transition-[width] duration-200 ease-out motion-reduce:transition-none"
                          style={{ width: `${(f.points / f.max) * 100}%` }}
                        />
                      </div>
                      <p className="mt-1 text-[13px] text-muted">{f.reason}</p>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}