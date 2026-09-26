export type TranscriptLine = {
  kind: 'cmd' | 'info' | 'error' | 'trace' | 'step' | 'ok' | 'pr';
  text: string;
  label?: string;
  delay?: number;
};

export const terminalTranscript: TranscriptLine[] = [
  { kind: 'cmd', text: 'pipelineiq watch acme/checkout-api', delay: 400 },
  { kind: 'info', text: 'listening for workflow_run events…', delay: 900 },
  { kind: 'error', text: '✗ ci #4812 failed · feat/multi-currency · 9f3c2e1 by @dana', delay: 500 },
  { kind: 'info', text: 'reading job log: build / test (2,341 lines)', delay: 450 },
  { kind: 'trace', text: "TypeError: Cannot read properties of undefined (reading 'currency')" },
  { kind: 'trace', text: '    at formatTotal (src/cart/total.ts:38:22)', delay: 450 },
  { kind: 'info', text: 'reading diff 9f3c2e1: 3 files, +42 −17', delay: 600 },
  { kind: 'step', label: 'diagnosis', text: 'CartLine.price became optional in src/types/cart.ts:12' },
  { kind: 'trace', text: 'formatTotal still reads price.currency with no guard · confidence 0.91', delay: 500 },
  { kind: 'step', label: 'patch', text: 'src/cart/total.ts +3 −1 · fall back to line.currency', delay: 350 },
  { kind: 'step', label: 'risk', text: '24 / 100 · failed_tests +20 · repeat_failure +4', delay: 350 },
  { kind: 'step', label: 'policy', text: 'auto-fix · under the 30-point threshold', delay: 450 },
  { kind: 'info', text: 'pushed pipelineiq/fix-4812 · re-running ci', delay: 900 },
  { kind: 'ok', text: '✓ 214 tests passed in 38s', delay: 400 },
  { kind: 'pr', text: '✓ opened PR #1907  fix(cart): guard optional price in formatTotal', delay: 300 },
  { kind: 'info', text: 'time to green: 41s · nobody was paged' },
];