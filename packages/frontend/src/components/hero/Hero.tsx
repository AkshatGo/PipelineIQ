import { useReducedMotion } from 'framer-motion';
import { PlayIcon } from 'lucide-react';
import { CircuitBoardScene } from './CircuitBoardScene';
import { HealedCounter } from './HealedCounter';
import { ConnectButton } from '../ConnectButton';

export function Hero() {
  const reduced = useReducedMotion() ?? false;

  return (
    <section id="top" className="relative overflow-hidden border-b border-line">
      <div
        className="pointer-events-none absolute inset-0 opacity-30 lg:left-[38%] lg:opacity-100"
        aria-hidden="true"
      >
        <CircuitBoardScene reducedMotion={reduced} />
      </div>

      <div className="relative z-10 mx-auto flex min-h-[640px] max-w-7xl items-center px-5 pb-20 pt-20 md:px-8 lg:min-h-[740px] lg:pb-28 lg:pt-24">
        <div className="max-w-[600px]">
          <h1 className="text-[46px] font-semibold leading-[1.02] tracking-[-0.035em] md:text-[58px] xl:text-[68px]">
            Your build broke at 2:14 a.m. It was green by 2:15.
          </h1>
          <p className="mt-6 max-w-[56ch] text-lg leading-relaxed text-muted md:text-xl">
            PipelineIQ reads the failing log next to the commit diff, finds the cause, scores how risky
            the fix is, then opens a pull request, asks in Slack, or blocks it. You set the rules.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <ConnectButton />
            <a
              href="#live-fix"
              className="inline-flex items-center gap-2 whitespace-nowrap rounded-md border border-line bg-ink/60 px-5 py-3 text-[16px] font-medium text-paper transition-colors duration-150 hover:border-muted"
            >
              <PlayIcon className="h-4 w-4 text-copper" aria-hidden="true" />
              Watch a real fix
            </a>
          </div>
          <HealedCounter reducedMotion={reduced} />
        </div>
      </div>
    </section>
  );
}