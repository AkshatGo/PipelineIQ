export type RepoStatus = 'green' | 'red' | 'fixing';

export type Repo = {
  name: string;
  status: RepoStatus;
  healed: number;
};

export type Incident = {
  id: string;
  repo: string;
  branch: string;
  error: string;
  risk: number;
  action: 'auto' | 'approval' | 'block';
  outcome: string;
  ttg: string;
  cause: string;
  patch: { sign: '+' | '-'; line: string }[];
  factors: [string, number][];
};

export const repos: Repo[] = [
  { name: 'checkout-api', status: 'green', healed: 214 },
  { name: 'web-storefront', status: 'fixing', healed: 167 },
  { name: 'payments-worker', status: 'red', healed: 88 },
  { name: 'mobile-app', status: 'green', healed: 139 },
  { name: 'search-indexer', status: 'green', healed: 61 },
  { name: 'infra-terraform', status: 'green', healed: 12 },
];

/** Median time-to-green in minutes, last 14 days */
export const timeToGreen = [38.2, 35.1, 36.4, 29.8, 24.5, 21.0, 17.3, 12.6, 9.4, 6.8, 3.9, 2.2, 1.1, 0.68];

export const incidents: Incident[] = [
  {
    id: '4812',
    repo: 'checkout-api',
    branch: 'feat/multi-currency',
    error: "TypeError: reading 'currency'",
    risk: 24,
    action: 'auto',
    outcome: 'PR #1907 merged',
    ttg: '41s',
    cause: 'CartLine.price became optional in src/types/cart.ts. formatTotal still read price.currency.',
    patch: [
      { sign: '-', line: 'const code = line.price.currency;' },
      { sign: '+', line: 'const code = line.price?.currency' },
      { sign: '+', line: '  ?? line.currency;' },
    ],
    factors: [
      ['failed_tests', 20],
      ['repeat_failure', 4],
    ],
  },
  {
    id: '3107',
    repo: 'payments-worker',
    branch: 'main',
    error: 'AssertionError: 10.05 != 10.04',
    risk: 55,
    action: 'approval',
    outcome: 'Waiting on @marco',
    ttg: '—',
    cause: 'Bumping babel 2.14 → 2.15 changed the default rounding mode used by src/money.py.',
    patch: [
      { sign: '-', line: 'return amount.quantize(CENTS)' },
      { sign: '+', line: 'return amount.quantize(' },
      { sign: '+', line: '  CENTS, rounding=ROUND_HALF_EVEN)' },
    ],
    factors: [
      ['production_branch', 25],
      ['failed_tests', 20],
      ['missing_review', 10],
    ],
  },
  {
    id: '2290',
    repo: 'web-storefront',
    branch: 'feat/new-nav',
    error: "Module not found: '@acme/ui/Button'",
    risk: 12,
    action: 'auto',
    outcome: 'PR #884 open',
    ttg: '1m 12s',
    cause: 'The design package renamed Button.tsx to button.tsx; the Linux runner is case-sensitive.',
    patch: [
      { sign: '-', line: "import { Button } from '@acme/ui/Button';" },
      { sign: '+', line: "import { Button } from '@acme/ui/button';" },
    ],
    factors: [
      ['change_size', 2],
      ['missing_review', 10],
    ],
  },
  {
    id: '5561',
    repo: 'infra-terraform',
    branch: 'main',
    error: 'Unsupported argument "acl"',
    risk: 78,
    action: 'block',
    outcome: 'Blocked · sensitive files',
    ttg: '—',
    cause: 'AWS provider v5 removed the inline acl argument from aws_s3_bucket.',
    patch: [
      { sign: '-', line: 'acl = "private"' },
      { sign: '+', line: 'resource "aws_s3_bucket_acl" "logs" {' },
      { sign: '+', line: '  acl = "private"' },
    ],
    factors: [
      ['production_branch', 25],
      ['sensitive_files', 25],
      ['missing_review', 10],
      ['change_size', 8],
      ['repeat_failure', 6],
      ['file_count', 4],
    ],
  },
  {
    id: '1408',
    repo: 'mobile-app',
    branch: 'release/3.2',
    error: 'ESLint: no-unused-vars (14)',
    risk: 6,
    action: 'auto',
    outcome: 'PR #562 merged',
    ttg: '33s',
    cause: 'A refactor left 14 unused imports across 12 screens; lint runs with --max-warnings 0.',
    patch: [
      { sign: '-', line: "import { useMemo } from 'react';" },
      { sign: '-', line: "import { Spacer } from '../ui';" },
    ],
    factors: [
      ['change_size', 2],
      ['file_count', 4],
    ],
  },
  {
    id: '977',
    repo: 'search-indexer',
    branch: 'feat/bulk-reindex',
    error: 'Timeout: test_reindex > 30s',
    risk: 29,
    action: 'auto',
    outcome: 'PR #341 merged',
    ttg: '2m 04s',
    cause: 'Reindex now writes one document per request; the test fixture grew to 40k docs.',
    patch: [
      { sign: '-', line: 'for doc in docs: client.index(doc)' },
      { sign: '+', line: 'helpers.bulk(client, docs, chunk_size=500)' },
    ],
    factors: [
      ['failed_tests', 20],
      ['repeat_failure', 8],
      ['change_size', 1],
    ],
  },
];