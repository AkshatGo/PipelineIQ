import { CheckIcon } from 'lucide-react';
import { comparisonRows } from '@/data/comparison';

export function ComparisonTable() {
  return (
    <section className="border-b border-line bg-ink-900 py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <h2 className="max-w-[20ch] text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
          What changes the morning after
        </h2>

        <div className="mt-12 overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left">
            <caption className="sr-only">Handling a failed build today compared with PipelineIQ</caption>
            <thead>
              <tr className="text-[14px] text-muted">
                <th scope="col" className="w-[24%] pb-4 pr-6 font-normal">
                  <span className="sr-only">Moment</span>
                </th>
                <th scope="col" className="w-[36%] pb-4 pr-6 font-normal">Today</th>
                <th scope="col" className="w-[40%] pb-4 font-medium text-paper">With PipelineIQ</th>
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row: typeof comparisonRows[0]) => (
                <tr key={row.moment} className="border-t border-line align-top">
                  <th scope="row" className="py-5 pr-6 text-[17px] font-semibold text-paper">
                    {row.moment}
                  </th>
                  <td className="py-5 pr-6 text-[16px] leading-relaxed text-muted">{row.today}</td>
                  <td className="py-5 text-[16px] leading-relaxed text-paper">
                    <span className="flex gap-2.5">
                      <CheckIcon className="mt-1 h-4 w-4 shrink-0 text-fix" aria-hidden="true" />
                      {row.withIQ}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}