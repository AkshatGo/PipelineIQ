import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { autofixReport } from '../api';
import { GitHubIcon } from '../components/ui/GitHubIcon';
import { SlackBotMessage } from '../components/slack/SlackBotMessage';

type PolicyAction = 'auto_fix' | 'approval_required' | 'block_only';

export function AutoFixReportPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [decision] = useState<'pending' | 'approved' | 'rejected'>('pending');

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['autofixReport', token],
    queryFn: () => autofixReport(token!),
    enabled: !!token,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-copper border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted">Loading report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center p-8">
          <svg className="w-16 h-16 text-fail mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77-1.333.192 3 1.732 3z" />
          </svg>
          <h2 className="mt-4 text-2xl font-semibold text-paper mb-2">Report not found</h2>
          <p className="text-muted mb-6">This auto-fix report could not be found or has expired.</p>
          <a
            href="/dashboard"
            className="rounded-md bg-copper px-4 py-2 text-sm font-semibold text-ink hover:brightness-110"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  const execution = report.execution;
  const copy: Record<PolicyAction, { title: string; detail: string }> = {
    auto_fix: {
      title: 'Auto-fix approved — PR opened',
      detail: 'The fix has been applied and a pull request has been opened. CI will re-run to verify the fix.',
    },
    approval_required: {
      title: 'Awaiting your decision',
      detail: 'Review the proposed fix below. Approve to open a PR, or reject to keep the fix for future reference.',
    },
    block_only: {
      title: 'Fix blocked by policy',
      detail: 'This fix exceeds the risk threshold for automatic application. It has been logged for review.',
    },
  };

  return (
    <section className="border-b border-line py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
              Auto-fix Report
            </h2>
            <p className="mt-6 max-w-[50ch] text-lg leading-relaxed text-muted">
              {copy[execution.policy_action as PolicyAction]?.detail || 'Review the proposed fix and decide whether to approve or reject.'}
            </p>
          </div>

          <div>
            <div className="overflow-hidden rounded-lg border border-line bg-ink-900">
              <div className="flex items-center justify-between border-b border-line px-5 py-3">
                <span className="flex items-center gap-1 font-semibold text-paper">
                  <GitHubIcon />
                  <span className="ml-2 font-semibold text-paper">PipelineIQ</span>
                  <span className="ml-2 rounded-sm bg-ink-700 px-1 text-[10px] font-medium text-muted">App</span>
                  <span className="text-[12px] text-muted">2:14 PM</span>
                </span>
              </div>
              <div className="mt-0.5 text-[15px] leading-relaxed text-paper">
                <p>
                  Medium-risk fix ready for <span className="font-mono text-[14px]">acme/payments-worker</span>. It
                  needs a human before it opens.
                </p>
                <div className="mt-3 border-l-[3px] border-copper pl-4">
                  <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-[72px_minmax(0,1fr)]">
                    <dt className="text-[13px] text-muted sm:pt-0.5">Failure</dt>
                    <dd className="text-[15px]">ci #3107 · main · test_refund_rounding</dd>
                    <dt className="text-[13px] text-muted sm:pt-0.5">Cause</dt>
                    <dd>Bumping babel 2.14 → 2.15 changed the default rounding in src/money.py</dd>
                    <dt className="text-[13px] text-muted sm:pt-0.5">Fix</dt>
                    <dd>Pin ROUND_HALF_EVEN in src/money.py (+2 −1)</dd>
                    <dt className="text-[13px] text-muted sm:pt-0.5">Risk</dt>
                    <dd>
                      <span className="font-mono text-[14px] font-medium text-copper">55 / 100</span>
                      <span className="mt-0.5 block font-mono text-[12px] text-muted">
                        production_branch +25 · failed_tests +20 · missing_review +10
                      </span>
                    </dd>
                  </dl>
                </div>
              </div>
            </div>

            <div className="space-y-6 px-5 py-6">
              <SlackBotMessage time="2:14 PM">
                <p>
                  Medium-risk fix ready for <span className="font-mono text-[14px]">acme/payments-worker</span>. It
                  needs a human before it opens.
                </p>
                <div className="mt-3 border-l-[3px] border-copper pl-4">
                  <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-[72px_minmax(0,1fr)]">
                    <dt className="text-[13px] text-muted sm:pt-0.5">Failure</dt>
                    <dd className="font-mono text-[13px]">ci #3107 · main · test_refund_rounding</dd>
                    <dt className="text-[13px] text-muted sm:pt-0.5">Cause</dt>
                    <dd>Bumping babel 2.14 → 2.15 changed the default rounding in src/money.py</dd>
                    <dt className="text-[13px] text-muted sm:pt-0.5">Fix</dt>
                    <dd>Pin ROUND_HALF_EVEN in src/money.py (+2 −1)</dd>
                    <dt className="text-[13px] text-muted sm:pt-0.5">Risk</dt>
                    <dd>
                      <span className="font-mono text-[14px] font-medium text-copper">55 / 100</span>
                      <span className="mt-0.5 block font-mono text-[12px] text-muted">
                        production_branch +25 · failed_tests +20 · missing_review +10
                      </span>
                    </dd>
                  </dl>
                </div>
              </SlackBotMessage>

              {decision === 'pending' ? (
                <p className="text-[13px] text-muted sm:pt-0.5">
                  by @marco at 2:16 PM
                </p>
              ) : (
                <div className="mt-6 flex flex-wrap gap-2">
                  <a
                    href="#dashboard"
                    className="whitespace-nowrap rounded-md px-2 py-1.5 text-[14px] text-teal-soft underline-offset-4 hover:underline"
                  >
                    View diff
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}