import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { CheckIcon, XIcon } from 'lucide-react';
import { ciErrors, ciFixes } from '@/data/ciErrors';

type StampState = 'failed' | 'fixed';

export function StampBand() {
  const reduced = useReducedMotion() ?? false;
  const [state, setState] = useState<StampState>('failed');

  useEffect(() => {
    if (reduced) return;
    const id = window.setInterval(() => setState((s) => (s === 'failed' ? 'fixed' : 'failed')), 2800);
    return () => window.clearInterval(id);
  }, [reduced]);

  const failed = state === 'failed';

  return (
    <section aria-label="Failures and their fixes" className="border-b border-line bg-ink-900">
      <div className="mx-auto grid max-w-7xl lg:grid-cols-[300px_minmax(0,1fr)]">
        <div className="flex h-44 items-center justify-center border-b border-line lg:h-auto lg:border-b-0 lg:border-r">
          <span className="sr-only">Every failed build becomes a fixed build.</span>
          <div className="relative flex h-20 w-56 items-center justify-center" aria-hidden="true">
            <AnimatePresence initial={false} mode="popLayout">
              <motion.div
                key={state}
                initial={reduced ? false : { scale: 1.9, rotate: -14, opacity: 0 }}
                animate={{ scale: [1.9, 0.94, 1], rotate: -6, opacity: 1 }}
                exit={{ opacity: 0, transition: { duration: 0.12, ease: 'easeOut' } }}
                transition={{ duration: 0.26, ease: [0.23, 1, 0.32, 1], times: [0, 0.7, 1] }}
                className={`absolute rounded-md border-[3px] px-6 py-2 font-mono text-[34px] font-semibold tracking-[0.1em] outline outline-1 outline-offset-[3px] ${
                  failed
                    ? 'border-fail text-fail-soft outline-fail/60'
                    : 'border-fix text-fix outline-fix/60'
                }`}
              >
                {failed ? 'FAILED' : 'FIXED'}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        <div className="space-y-3 overflow-hidden py-7">
          <TickerRow items={ciErrors} tone="fail" />
          <TickerRow items={ciFixes} tone="fix" />
        </div>
      </div>
    </section>
  );
}

type TickerRowProps = { items: string[]; tone: 'fail' | 'fix' };

function TickerRow({ items, tone }: TickerRowProps) {
  const isFail = tone === 'fail';
  const doubled = [...items, ...items];
  return (
    <div className="overflow-hidden motion-reduce:overflow-x-auto">
      <ul
        className={`flex w-max gap-3 px-3 hover:[animation-play-state:paused] motion-reduce:animate-none ${
          isFail ? 'animate-marquee-left' : 'animate-marquee-right'
        }`}
      >
        {doubled.map((text, i) => (
          <li
            key={`${text}-${i}`}
            aria-hidden={i >= items.length}
            className="flex items-center gap-2.5 whitespace-nowrap rounded border border-line bg-ink px-3.5 py-2 font-mono text-[13px] text-paper/90"
          >
            {isFail ? (
              <XIcon className="h-3.5 w-3.5 shrink-0 text-fail-soft" aria-hidden="true" />
            ) : (
              <CheckIcon className="h-3.5 w-3.5 shrink-0 text-fix" aria-hidden="true" />
            )}
            {text}
          </li>
        ))}
      </ul>
    </div>
  );
}