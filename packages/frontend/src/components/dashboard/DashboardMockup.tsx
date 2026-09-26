import { useState } from 'react';
import { GitBranchIcon } from 'lucide-react';
import { incidents, repos, timeToGreen, Incident, RepoStatus } from '@/data/dashboard';
import { riskTextClass } from '@/utils/risk';
import { Sparkline } from './Sparkline';
import { Logo } from '../Logo';

const statusDot: Record<RepoStatus, string> = {
  green: 'bg-fix',
  red: 'bg-fail',
  fixing: 'bg-copper',
};

const actionChip: Record<Incident['action'], { label: string; cls: string }> = {
  auto: { label: 'auto-fix', cls: 'bg-teal text-paper border-teal' },
  approval: { label: 'approval', cls: 'border-copper text-copper' },
  block: { label: 'blocked', cls: 'border-fail text-fail-soft' },
};

export function DashboardMockup() {
  const [selectedId, setSelectedId] = useState(incidents[0].id);
  const selected = incidents.find((i) => i.id === selectedId) ?? incidents[0];

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-ink-900 text-left shadow-[0_50px_100px_-40px_rgba(0,0,0,0.8)]">
      <div className="flex items-center justify-between border-b border-line bg-ink-800 px-4 py-2.5">
        <Logo className="h-5 w-5" />
        <span className="font-mono text-[12px] text-muted">app.pipelineiq.dev/acme</span>
      </div>

      <div className="grid lg:grid-cols-[200px_minmax(0,1fr)_280px]">
        {/* Repos */}
        <aside className="hidden border-r border-line p-4 lg:block" aria-label="Repositories">
          <p className="mb-3 text-[13px] text-muted">Repositories</p>
          <ul className="space-y-0.5">
            {repos.map((r) => (
              <li
                key={r.name}
                className={`flex items-center justify-between rounded px-2 py-1.5 text-[13px] ${
                  r.name === selected.repo ? 'bg-ink-700 text-paper' : 'text-muted'
                }`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusDot[r.status]}`} />
                  <span className="truncate">{r.name}</span>
                </span>
                <span className="font-mono text-[11px] text-muted">{r.healed}</span>
              </li>
            ))}
          </ul>
        </aside>

        {/* Main */}
        <div className="min-w-0 p-5">
          <div className="grid gap-6 border-b border-line pb-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <div>
              <p className="text-[13px] text-muted">Median time-to-green · 14 days</p>
              <p className="mt-1 font-mono text-[34px] font-medium leading-none text-paper">
                41s <span className="text-[14px] text-fix">from 38m 12s</span>
              </p>
              <div className="mt-3">
                <Sparkline values={timeToGreen} />
              </div>
            </div>
            <dl className="grid grid-cols-3 gap-5 md:grid-cols-1 md:gap-3 md:text-right">
              <div>
                <dt className="text-[12px] text-muted">Fixed on its own</dt>
                <dd className="font-mono text-lg text-paper">71%</dd>
              </div>
              <div>
                <dt className="text-[12px] text-muted">Awaiting approval</dt>
                <dd className="font-mono text-lg text-copper">1</dd>
              </div>
              <div>
                <dt className="text-[12px] text-muted">Blocked</dt>
                <dd className="font-mono text-lg text-fail-soft">1</dd>
              </div>
            </dl>
          </div>

          <table className="mt-3 w-full text-[13px]">
            <caption className="sr-only">Recent incidents</caption>
            <thead>
              <tr className="text-left text-[12px] text-muted">
                <th scope="col" className="py-2 pr-3 font-normal">Run</th>
                <th scope="col" className="py-2 pr-3 font-normal">Failure</th>
                <th scope="col" className="py-2 pr-3 text-right font-normal">Risk</th>
                <th scope="col" className="hidden py-2 pr-3 font-normal sm:table-cell">Action</th>
                <th scope="col" className="hidden py-2 text-right font-normal xl:table-cell">To green</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc) => {
                const active = inc.id === selected.id;
                const chip = actionChip[inc.action];
                return (
                  <tr
                    key={inc.id}
                    onClick={() => setSelectedId(inc.id)}
                    className={`cursor-pointer border-t border-line transition-colors duration-150 ${
                      active ? 'bg-ink-700' : 'hover:bg-ink-800'
                    }`}
                  >
                    <td className="py-2.5 pl-2 pr-3 align-top">
                      <button
                        type="button"
                        onClick={() => setSelectedId(inc.id)}
                        aria-pressed={active}
                        className="whitespace-nowrap rounded-sm font-mono text-paper"
                      >
                        #{inc.id}
                      </button>
                      <div className="text-[12px] text-muted">{inc.repo}</div>
                    </td>
                    <td className="max-w-[220px] truncate py-2.5 pr-3 align-top font-mono text-[12px] text-paper/90">
                      {inc.error}
                    </td>
                    <td className={`py-2.5 pr-3 text-right align-top font-mono ${riskTextClass(inc.risk)}`}>
                      {inc.risk}
                    </td>
                    <td className="hidden py-2.5 pr-3 align-top sm:table-cell">
                      <span className={`inline-block whitespace-nowrap rounded-sm border px-1.5 py-px font-mono text-[11px] ${chip.cls}`}>
                        {chip.label}
                      </span>
                    </td>
                    <td className="hidden py-2.5 pr-2 text-right align-top font-mono text-muted xl:table-cell">{inc.ttg}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Detail */}
        <aside className="hidden border-l border-line bg-ink-800/60 p-5 lg:block" aria-label="Incident detail">
          <p className="font-mono text-[12px] text-muted">
            {selected.repo} #{selected.id}
          </p>
          <p className="mt-1 flex items-center gap-1.5 font-mono text-[12px] text-muted">
            <GitBranchIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {selected.branch}
          </p>
          <h3 className="mt-4 text-[13px] text-muted">Root cause</h3>
          <p className="mt-1 text-[14px] leading-snug text-paper">{selected.cause}</p>
          <h3 className="mt-4 text-[13px] text-muted">Patch</h3>
          <pre className="mt-1.5 overflow-x-auto rounded border border-line bg-ink p-2.5 font-mono text-[11.5px] leading-relaxed">
            {selected.patch.map((p, i) => (
              <div key={i} className={p.sign === '+' ? 'text-fix' : 'text-fail-soft'}>
                {p.sign} {p.line}
              </div>
            ))}
          </pre>
          <h3 className="mt-4 flex items-baseline justify-between text-[13px] text-muted">
            Risk
            <span className={`font-mono text-[15px] ${riskTextClass(selected.risk)}`}>{selected.risk} / 100</span>
          </h3>
          <ul className="mt-1.5 space-y-1">
            {selected.factors.map(([name, pts]) => (
              <li key={name} className="flex justify-between font-mono text-[11.5px]">
                <span className="text-muted">{name}</span>
                <span className="text-paper">+{pts}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 border-t border-line pt-3 text-[13px] text-paper">{selected.outcome}</p>
        </aside>
      </div>
    </div>
  );
}