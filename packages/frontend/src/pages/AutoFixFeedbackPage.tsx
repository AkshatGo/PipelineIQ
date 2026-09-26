import React, { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { XCircleIcon } from 'lucide-react';
import { SlackBotMessage } from '../components/slack/SlackBotMessage';
import { autofixFeedback } from '../api';

export function AutoFixFeedbackPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [submitted, setSubmitted] = useState(false);
  const [formData, setFormData] = useState({
    outcome: '',
    automation_quality: '',
    should_auto_apply_similar: false,
    notes: '',
  });

  const { data: feedback, isLoading, error } = useQuery({
    queryKey: ['autofixFeedback', token],
    queryFn: () => autofixFeedback(token!),
    enabled: !!token,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    // TODO: Implement feedback submission
    // await autofixFeedbackSubmit(token, formData);
    setSubmitted(true);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-copper border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted">Loading feedback form...</p>
        </div>
      </div>
    );
  }

  if (error || !feedback) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center p-8">
          <XCircleIcon className="w-16 h-16 text-fail mx-auto mb-4" />
          <h2 className="mt-4 text-2xl font-semibold text-paper mb-2">Feedback not found</h2>
          <p className="text-muted mb-6">This feedback form could not be found or has expired.</p>
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

  if (submitted) {
    return (
      <section className="border-b border-line py-24 lg:py-32">
        <div className="mx-auto max-w-7xl px-5 md:px-8">
          <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
            <div>
              <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
                Feedback submitted — thank you!
              </h2>
              <p className="mt-6 max-w-[50ch] text-lg leading-relaxed text-muted">
                Your feedback helps improve PipelineIQ's auto-fix quality. The team will review your input.
              </p>
            </div>
            <div className="mt-6">
              <a
                href={`/workspace/${workspaceId}`}
                className="inline-flex items-center gap-1.5 rounded-md bg-signal px-3.5 py-1.5 text-[14px] font-semibold text-ink transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.97]"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Workspace
              </a>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="border-b border-line py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
              How did the auto-fix work out?
            </h2>
            <p className="mt-6 max-w-[50ch] text-lg leading-relaxed text-muted">
              Your feedback helps PipelineIQ learn. Approved fixes that worked well get prioritized for
              future auto-merging. Rejected fixes teach the system what to avoid.
            </p>
          </div>

          <div>
            <div className="overflow-hidden rounded-lg border border-line bg-ink-900">
              <div className="flex items-center justify-between border-b border-line px-5 py-3">
                <span className="flex items-center gap-1 font-semibold text-paper">
                  <svg className="h-4 w-4 text-muted" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                  </svg>
                  <span className="ml-2 font-semibold text-paper">PipelineIQ</span>
                  <span className="ml-2 rounded-sm bg-ink-700 px-1 text-[10px] font-medium text-muted">App</span>
                  <span className="text-[12px] text-muted">2:14 PM</span>
                </span>
              </div>

              <div className="space-y-6 px-5 py-6">
                <SlackBotMessage time="2:14 PM">
                  <p>
                    Medium-risk fix ready for <span className="font-mono text-[14px]">acme/payments-worker</span>. It
                    needs a human before it opens.
                  </p>
                  <div className="mt-3 border-l-[3px] border-copper pl-4">
                    <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-[72px_minmax(0,1fr)]">
                      {[
                        { label: 'Failure', value: 'ci #3107 · main · test_refund_rounding', mono: true },
                        { label: 'Cause', value: 'Bumping babel 2.14 → 2.15 changed the default rounding in src/money.py', mono: false },
                        { label: 'Fix', value: 'Pin ROUND_HALF_EVEN in src/money.py (+2 −1)', mono: false },
                      ].map((f) => (
                        <React.Fragment key={f.label}>
                          <dt className="text-[13px] text-muted sm:pt-0.5">{f.label}</dt>
                          <dd className={f.mono ? 'font-mono text-[13px]' : 'text-[15px]'}>{f.value}</dd>
                        </React.Fragment>
                      ))}
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

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-muted mb-2">Outcome</label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="outcome"
                          value="success"
                          checked={formData.outcome === 'success'}
                          onChange={(e) => setFormData({ ...formData, outcome: e.target.value })}
                          className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper"
                        />
                        <span className="text-paper">Fixed — CI passes</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="outcome"
                          value="partial"
                          checked={formData.outcome === 'partial'}
                          onChange={(e) => setFormData({ ...formData, outcome: e.target.value })}
                          className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper"
                        />
                        <span className="text-paper">Partial — needs more work</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="outcome"
                          value="wrong"
                          checked={formData.outcome === 'wrong'}
                          onChange={(e) => setFormData({ ...formData, outcome: e.target.value })}
                          className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper"
                        />
                        <span className="text-paper">Wrong fix — introduced issues</span>
                      </label>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-muted mb-2">Automation Quality</label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="automation_quality"
                          value="great"
                          checked={formData.automation_quality === 'great'}
                          onChange={(e) => setFormData({ ...formData, automation_quality: e.target.value })}
                          className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper"
                        />
                        <span className="text-paper">Great — minimal changes, correct fix</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="automation_quality"
                          value="ok"
                          checked={formData.automation_quality === 'ok'}
                          onChange={(e) => setFormData({ ...formData, automation_quality: e.target.value })}
                          className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper"
                        />
                        <span className="text-paper">OK — works but could be cleaner</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="automation_quality"
                          value="poor"
                          checked={formData.automation_quality === 'poor'}
                          onChange={(e) => setFormData({ ...formData, automation_quality: e.target.value })}
                          className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper"
                        />
                        <span className="text-paper">Poor — messy or over-engineered</span>
                      </label>
                    </div>
                  </div>

                  <div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.should_auto_apply_similar}
                        onChange={(e) => setFormData({ ...formData, should_auto_apply_similar: e.target.checked })}
                        className="w-4 h-4 text-copper border-line bg-ink focus:ring-copper rounded"
                      />
                      <span className="text-paper">Auto-apply similar fixes in the future</span>
                    </label>
                  </div>

                  <div>
                    <label htmlFor="notes" className="block text-sm font-medium text-muted mb-2">
                      Additional Notes (optional)
                    </label>
                    <textarea
                      id="notes"
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      rows={4}
                      className="w-full rounded-md border border-line bg-ink px-4 py-2.5 text-paper placeholder-muted focus:border-copper focus:outline-none focus:ring-2 focus:ring-copper/20 resize-none"
                      placeholder="Any other context for the team..."
                    />
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="submit"
                      disabled={!formData.outcome || !formData.automation_quality}
                      className="whitespace-nowrap rounded-md bg-fix px-3.5 py-1.5 text-[14px] font-semibold text-ink transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Submit Feedback
                    </button>
                    <a
                      href="#dashboard"
                      className="whitespace-nowrap rounded-md px-2 py-1.5 text-[14px] text-teal-soft underline-offset-4 hover:underline"
                    >
                      View diff
                    </a>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}