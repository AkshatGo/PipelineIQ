import { TiltCard } from './TiltCard';
import { Terminal } from './Terminal';

const facts = [
  { label: 'Log lines read', value: '2,341' },
  { label: 'Files patched', value: '1' },
  { label: 'Time to green', value: '41s' },
];

export function TerminalDemo() {
  return (
    <section id="live-fix" className="border-b border-line py-24 lg:py-32">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div>
          <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
            One failure, start to finish
          </h2>
          <p className="mt-6 max-w-[52ch] text-lg leading-relaxed text-muted">
            A type change in one file broke a function in another. The log only showed the crash; the
            diff showed why. PipelineIQ read both, patched one line, and re-ran CI before opening the PR.
          </p>
          <dl className="mt-10 grid max-w-md grid-cols-3 border-t border-line pt-5">
            {facts.map((f) => (
              <div key={f.label}>
                <dt className="text-sm text-muted">{f.label}</dt>
                <dd className="mt-1 font-mono text-2xl text-paper">{f.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <TiltCard>
          <Terminal />
        </TiltCard>
      </div>
    </section>
  );
}