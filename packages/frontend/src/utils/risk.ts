export type RiskSignals = {
  branch: 'main' | 'feature';
  linesChanged: number;
  filesChanged: number;
  testsFailed: boolean;
  sensitiveFiles: boolean;
  hasReview: boolean;
  priorFailures: number;
};

export type RiskFactor = {
  key: string;
  points: number;
  max: number;
  reason: string;
};

export type RiskAction = 'auto_fix' | 'approval' | 'block';
export type RiskBand = 'low' | 'medium' | 'high';

export type RiskAssessment = {
  score: number;
  band: RiskBand;
  action: RiskAction;
  factors: RiskFactor[];
};

export const AUTO_FIX_BELOW = 30;
export const APPROVAL_BELOW = 60;

/** Mirrors the deterministic scorer in packages/backend/services/risk.py */
export function assessRisk(s: RiskSignals): RiskAssessment {
  const factors: RiskFactor[] = [
    {
      key: 'production_branch',
      points: s.branch === 'main' ? 25 : 0,
      max: 25,
      reason: s.branch === 'main' ? 'Targets the protected main branch' : 'Targets a feature branch',
    },
    {
      key: 'failed_tests',
      points: s.testsFailed ? 20 : 0,
      max: 20,
      reason: s.testsFailed ? 'The pipeline has failing tests' : 'No failing tests',
    },
    {
      key: 'sensitive_files',
      points: s.sensitiveFiles ? 25 : 0,
      max: 25,
      reason: s.sensitiveFiles ? 'Touches auth, deploy, or dependency files' : 'No sensitive files touched',
    },
    {
      key: 'change_size',
      points: Math.min(20, Math.floor(s.linesChanged / 50)),
      max: 20,
      reason: `${s.linesChanged} lines changed`,
    },
    {
      key: 'file_count',
      points: Math.min(10, Math.floor(s.filesChanged / 3)),
      max: 10,
      reason: `${s.filesChanged} ${s.filesChanged === 1 ? 'file' : 'files'} changed`,
    },
    {
      key: 'missing_review',
      points: s.hasReview ? 0 : 10,
      max: 10,
      reason: s.hasReview ? 'Required review is in place' : 'No required review approval',
    },
    {
      key: 'repeat_failure',
      points: Math.min(10, s.priorFailures * 2),
      max: 10,
      reason: `${s.priorFailures} similar ${s.priorFailures === 1 ? 'failure' : 'failures'} before`,
    },
  ];

  const score = Math.min(100, factors.reduce((sum, f) => sum + f.points, 0));
  const band: RiskBand = score < 30 ? 'low' : score < 60 ? 'medium' : 'high';
  const action: RiskAction =
    score < AUTO_FIX_BELOW ? 'auto_fix' : score < APPROVAL_BELOW ? 'approval' : 'block';

  return { score, band, action, factors };
}

export function riskTextClass(score: number): string {
  if (score < AUTO_FIX_BELOW) return 'text-fix';
  if (score < APPROVAL_BELOW) return 'text-copper';
  return 'text-fail-soft';
}