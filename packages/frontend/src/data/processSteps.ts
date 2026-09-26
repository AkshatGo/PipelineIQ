export type ProcessStep = {
  title: string;
  description: string;
  tag: string;
  tone: 'fail' | 'copper' | 'fix';
};

export const processSteps: ProcessStep[] = [
  {
    title: 'Detect',
    description: 'A webhook lands the second a job goes red. No polling, no cron.',
    tag: 'workflow_run.completed',
    tone: 'fail',
  },
  {
    title: 'Diagnose',
    description: 'The failing log is read next to the commit diff to find the line that caused it.',
    tag: 'log + diff',
    tone: 'copper',
  },
  {
    title: 'Score',
    description: 'Seven signals add up to a 0–100 risk score, and every point says why.',
    tag: 'score 0–100',
    tone: 'copper',
  },
  {
    title: 'Decide',
    description: 'Your policy picks: open a PR, ask in Slack, or block the change.',
    tag: 'auto · approve · block',
    tone: 'copper',
  },
  {
    title: 'Fix',
    description: 'A patch branch is pushed and CI re-runs before any pull request opens.',
    tag: 'PR #1907',
    tone: 'fix',
  },
  {
    title: 'Learn',
    description: 'Merged, edited, or rejected, the outcome is saved so the same failure goes faster next time.',
    tag: 'memory +1 pattern',
    tone: 'fix',
  },
];