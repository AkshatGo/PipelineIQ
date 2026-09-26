import { processSteps, ProcessStep } from '@/data/processSteps';

const toneClass: Record<ProcessStep['tone'], string> = {
  fail: 'border-fail text-fail-soft',
  copper: 'border-copper text-copper',
  fix: 'border-fix text-fix',
};

export function ProcessSteps() {
  return (
    <section id="how-it-works" className="border-b border-line bg-ink-900 py-24 lg:py-32">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-20">
        <div className="self-start lg:sticky lg:top-28">
          <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
            Six steps from red to green
          </h2>
          <p className="mt-6 max-w-[46ch] text-lg leading-relaxed text-muted">
            Every step writes to an audit log you can open from the dashboard. Nothing reaches your
            default branch without a pull request.
          </p>
        </div>

        <ol className="relative">
          <span aria-hidden="true" className="absolute bottom-10 left-[19px] top-10 w-px bg-copper/40" />
          {processSteps.map((step: ProcessStep, i: number) => (
            <li
              key={step.title}
              className="relative grid grid-cols-[40px_minmax(0,1fr)] gap-x-5 border-b border-line py-7 last:border-b-0 md:grid-cols-[40px_minmax(0,1fr)_auto] md:items-baseline"
            >
              <span
                className={`flex h-10 w-10 items-center justify-center rounded-full border-2 bg-ink-900 font-mono text-sm font-medium md:self-start ${toneClass[step.tone]}`}
              >
                {i + 1}
              </span>
              <div>
                <h3 className="text-xl font-semibold">{step.title}</h3>
                <p className="mt-1.5 max-w-[52ch] text-[16px] leading-relaxed text-muted">{step.description}</p>
                <code className="mt-3 inline-block rounded border border-line px-2 py-0.5 font-mono text-[12px] text-muted md:hidden">
                  {step.tag}
                </code>
              </div>
              <code className="hidden whitespace-nowrap rounded border border-line px-2 py-0.5 font-mono text-[12px] text-muted md:inline-block">
                {step.tag}
              </code>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}