import React, { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { CheckIcon, GitPullRequestIcon, HashIcon, RotateCcwIcon, XIcon } from 'lucide-react';
import { SlackBotMessage } from './SlackBotMessage';

type Decision = 'pending' | 'approved' | 'rejected';

const fields = [
  { label: 'Failure', value: 'ci #3107 · main · test_refund_rounding', mono: true },
  { label: 'Cause', value: 'Bumping babel 2.14 → 2.15 changed the default rounding in src/money.py', mono: false },
  { label: 'Fix', value: 'Pin ROUND_HALF_EVEN in src/money.py (+2 −1)', mono: false },
];

export function SlackApproval() {
  const [decision, setDecision] = useState<Decision>('pending');
  const reduced = useReducedMotion() ?? false;

  return (
    <section className="border-b border-line py-24 lg:py-32">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 md:px-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div>
          <h2 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
            Medium risk? It asks in Slack first.
          </h2>
          <p className="mt-6 max-w-[50ch] text-lg leading-relaxed text-muted">
            Scores from 30 to 59 go to the channel you pick, with the cause, the patch, and every point of
            the score. Approve and the PR opens. Reject and that fix is never suggested for this repo again.
          </p>
          <p className="mt-6 text-[15px] text-muted">Try the buttons.</p>
        </div>

        <div>
          <div className="overflow-hidden rounded-lg border border-line bg-ink-900">
            <div className="flex items-center justify-between border-b border-line px-5 py-3">
              <span className="flex items-center gap-1 font-semibold text-paper">
                <HashIcon className="h-4 w-4 text-muted" aria-hidden="true" />
                ci-alerts
              </span>
              <span className="text-[13px] text-muted">14 members</span>
            </div>

            <div className="space-y-6 px-5 py-6">
              <SlackBotMessage time="2:14 PM">
                <p>
                  Medium-risk fix ready for <span className="font-mono text-[14px]">acme/payments-worker</span>. It
                  needs a human before it opens.
                </p>
                <div className="mt-3 border-l-[3px] border-copper pl-4">
                  <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-[72px_minmax(0,1fr)]">
                    {fields.map((f) => (
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

                {decision === 'pending' ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setDecision('approved')}
                      className="whitespace-nowrap rounded-md bg-fix px-3.5 py-1.5 text-[14px] font-semibold text-ink transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.97]"
                    >
                      Approve and open PR
                    </button>
                    <button
                      type="button"
                      onClick={() => setDecision('rejected')}
                      className="whitespace-nowrap rounded-md border border-line px-3.5 py-1.5 text-[14px] font-medium text-paper transition-[border-color,transform] duration-150 hover:border-fail active:scale-[0.97]"
                    >
                      Reject
                    </button>
                    <a
                      href="#dashboard"
                      className="whitespace-nowrap rounded-md px-2 py-1.5 text-[14px] text-teal-soft underline-offset-4 hover:underline"
                    >
                      View diff
                    </a>
                  </div>
                ) : (
                  <p
                    className={`mt-4 flex items-center gap-1.5 text-[14px] ${
                      decision === 'approved' ? 'text-fix' : 'text-fail-soft'
                    }`}
                  >
                    {decision === 'approved' ? (
                      <CheckIcon className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <XIcon className="h-4 w-4" aria-hidden="true" />
                    )}
                    {decision === 'approved' ? 'Approved' : 'Rejected'} by @marco at 2:16 PM
                  </p>
                )}
              </SlackBotMessage>

              <AnimatePresence initial={false}>
                {decision !== 'pending' && (
                  <motion.div
                    key={decision}
                    initial={reduced ? false : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, transition: { duration: 0.12 } }}
                    transition={{ duration: 0.22, ease: [0.23, 1, 0.32, 1] }}
                    aria-live="polite"
                  >
                    <SlackBotMessage time="2:17 PM">
                      {decision === 'approved' ? (
                        <>
                          <p>
                            Opened the PR. CI re-ran: 312 tests passed in 52s.{' '}
                            <span className="font-mono text-[14px]">main</span> is green.
                          </p>
                          <span className="mt-2 inline-flex items-center gap-2 rounded-md border border-line bg-ink px-3 py-1.5 font-mono text-[13px]">
                            <GitPullRequestIcon className="h-4 w-4 text-fix" aria-hidden="true" />
                            #1911 fix(money): pin ROUND_HALF_EVEN
                          </span>
                        </>
                      ) : (
                        <p>
                          Got it. ci #3107 stays open and is assigned to @dana. This fix is saved as rejected for
                          payments-worker, so it won't be proposed again.
                        </p>
                      )}
                    </SlackBotMessage>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
          {decision !== 'pending' && (
            <button
              type="button"
              onClick={() => setDecision('pending')}
              className="mt-3 inline-flex items-center gap-1.5 rounded text-[14px] text-muted transition-colors duration-150 hover:text-paper"
            >
              <RotateCcwIcon className="h-3.5 w-3.5" aria-hidden="true" />
              Reset the message
            </button>
          )}
        </div>
      </div>
    </section>
  );
}