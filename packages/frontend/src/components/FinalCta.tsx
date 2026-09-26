import { ConnectButton } from './ConnectButton';

export function FinalCta() {
  return (
    <section id="connect" className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="rounded-lg bg-signal p-px">
          <div className="grid gap-10 rounded-[7px] bg-ink-900 px-6 py-14 md:px-14 md:py-20 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <h2 className="max-w-[18ch] text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
                Next time a build breaks, read about it after it's fixed.
              </h2>
              <p className="mt-6 max-w-[56ch] text-lg leading-relaxed text-muted">
                Install on one repo in about two minutes. PipelineIQ starts watching from the next workflow
                run and never merges on its own.
              </p>
            </div>
            <div className="flex flex-col items-start gap-4">
              <ConnectButton href="/api/auth/github" />
              <p className="font-mono text-[12px] leading-relaxed text-muted">
                Read-only log access · you pick the repos
                <br />
                Every fix goes through a pull request
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}