import { XIcon, GitBranchIcon, AlertTriangleIcon, CheckCircleIcon, ClockIcon, RefreshCwIcon, ArrowUpRightIcon, GitCommitIcon, FileTextIcon, GitPullRequestIcon } from 'lucide-react';
import type { PipelineRunResponse } from "@pipelineiq/shared";
import { riskTextClass } from '../../utils/risk';

interface RunDetailPanelProps {
  run: PipelineRunResponse;
  onClose: () => void;
}

export function RunDetailPanel({ run, onClose }: RunDetailPanelProps) {
  const riskConfig = {
    low: { dot: 'bg-fix', label: 'Low', text: 'text-fix' },
    medium: { dot: 'bg-copper', label: 'Medium', text: 'text-copper' },
    high: { dot: 'bg-fail', label: 'High', text: 'text-fail' },
  };

  const getRiskBand = (score: number | null | undefined): keyof typeof riskConfig => {
    if (!score || score < 30) return 'low';
    if (score < 70) return 'medium';
    return 'high';
  };

  const riskBand = getRiskBand(run.risk_score);
  const risk = riskConfig[riskBand];

  const actionConfig = {
    auto_fix: { label: 'Auto-fix', cls: 'bg-teal text-paper border-teal' },
    approval_required: { label: 'Approval Required', cls: 'border-copper text-copper' },
    block_only: { label: 'Blocked', cls: 'border-fail text-fail-soft' },
  };

  const action = run.autofix_mode ? actionConfig[run.autofix_mode as keyof typeof actionConfig] : null;

  const statusConfig = {
    success: { icon: CheckCircleIcon, color: 'text-fix', bg: 'bg-fix/20', border: 'border-fix/30' },
    failure: { icon: AlertTriangleIcon, color: 'text-fail', bg: 'bg-fail/20', border: 'border-fail/30' },
    running: { icon: RefreshCwIcon, color: 'text-copper', bg: 'bg-copper/20', border: 'border-copper/30' },
    pending: { icon: ClockIcon, color: 'text-muted', bg: 'bg-muted/20', border: 'border-muted/30' },
  };

  const status = run.conclusion || run.workflow_status || 'pending';
  const statusCfg = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;

  const formatDuration = (startedAt: string | null | undefined, completedAt: string | null | undefined) => {
    if (!startedAt) return '—';
    const start = new Date(startedAt).getTime();
    const end = completedAt ? new Date(completedAt).getTime() : Date.now();
    const diff = Math.max(0, end - start);
    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="font-semibold text-paper">Run Details</h3>
          <p className="text-sm text-muted mt-0.5">#{run.run_id} · {run.branch || '—'}</p>
        </div>
        <button
          onClick={onClose}
          className="text-muted hover:text-paper transition-colors p-1"
          aria-label="Close detail panel"
        >
          <XIcon className="h-5 w-5" />
        </button>
      </div>

      <div className="space-y-6">
        {/* Status & Risk */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-1">Status</p>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full ${statusCfg.bg} border ${statusCfg.border}`}>
                <statusCfg.icon className={`h-4 w-4 ${statusCfg.color}`} />
              </span>
              <span className="font-medium text-paper capitalize">{status}</span>
            </div>
          </div>

          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-1">Risk Score</p>
            <div className="flex items-center gap-3">
              <span className={`font-mono text-2xl font-medium ${riskTextClass(run.risk_score || 0)}`}>
                {run.risk_score ?? '—'}
              </span>
              <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[11px] font-medium border ${risk.text} ${risk.dot}/20 border-current`}>
                <span className={`h-1.5 w-1.5 rounded-full ${risk.dot}`} />
                {risk.label}
              </span>
            </div>
          </div>
        </div>

        {/* Auto-fix Action */}
        {action && (
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-1">Auto-fix Action</p>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[12px] font-mono border ${action.cls}`}>
              {action.label}
            </span>
          </div>
        )}

        {/* Timing */}
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-1">Started</p>
            <p className="font-mono text-paper">
              {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
            </p>
          </div>
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-1">Completed</p>
            <p className="font-mono text-paper">
              {run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}
            </p>
          </div>
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-1">Duration</p>
            <p className="font-mono text-paper">{formatDuration(run.started_at, run.completed_at)}</p>
          </div>
        </div>

        {/* Repository Info */}
        <div className="rounded-lg border border-line bg-ink p-4">
          <p className="text-[12px] text-muted mb-2">Repository</p>
          <div className="flex items-center gap-3">
            <GitBranchIcon className="h-5 w-5 text-copper" />
            <div>
              <p className="font-medium text-paper">{run.repo_full_name || '—'}</p>
              <p className="text-sm text-muted">Branch: <span className="font-mono">{run.branch || '—'}</span></p>
            </div>
          </div>
        </div>

        {/* Commit Info */}
        {run.commit_sha && (
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-2">Commit</p>
            <div className="flex items-center gap-3">
              <GitCommitIcon className="h-5 w-5 text-copper" />
              <div>
                <p className="font-mono text-paper">{run.commit_sha.slice(0, 8)}</p>
                <p className="text-sm text-muted">{run.commit_message || 'No message'}</p>
              </div>
              {run.commit_url && (
                <a
                  href={run.commit_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-auto text-teal-soft hover:underline text-sm"
                >
                  <ArrowUpRightIcon className="h-4 w-4 inline-block" />
                  View on GitHub
                </a>
              )}
            </div>
          </div>
        )}

        {/* Workflow Info */}
        {run.workflow_name && (
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-2">Workflow</p>
            <div className="flex items-center gap-3">
              <FileTextIcon className="h-5 w-5 text-copper" />
              <p className="font-medium text-paper">{run.workflow_name}</p>
            </div>
          </div>
        )}

        {run.autofix_pr_url && (
          <div className="rounded-lg border border-line bg-ink p-4">
            <p className="text-[12px] text-muted mb-2">Auto-fix PR</p>
            <a
              href={run.autofix_pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-teal-soft hover:underline"
            >
              <GitPullRequestIcon className="h-4 w-4" />
              View Pull Request
            </a>
          </div>
        )}

        <div className="pt-4 border-t border-line">
          <button
            onClick={onClose}
            className="w-full rounded-md border border-line bg-ink px-4 py-2 text-sm font-medium text-muted hover:bg-ink-800 hover:text-paper transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}