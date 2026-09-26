export const comparisonRows = [
  {
    moment: 'Noticing a failure',
    today: 'Someone spots the red X in a PR, or a Slack ping hours later',
    withIQ: 'A webhook fires the moment a job fails',
  },
  {
    moment: 'Finding the cause',
    today: 'Scroll 2,000 log lines, then diff the last few commits by hand',
    withIQ: 'Log and diff are read together; the cause is pinned to a file and line',
  },
  {
    moment: 'Writing the fix',
    today: 'Switch context, branch, patch, push, wait for CI',
    withIQ: 'A patch branch is pushed and CI re-runs before a PR opens',
  },
  {
    moment: 'Deciding if it\'s safe',
    today: 'Gut feeling, or whoever happens to be online',
    withIQ: 'A 0–100 score from seven signals, with every point explained',
  },
  {
    moment: 'The same failure next month',
    today: 'Fixed from scratch, again',
    withIQ: 'Pattern is stored: fixed faster, or blocked if it was rejected',
  },
];