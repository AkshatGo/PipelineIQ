import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { riskTextClass } from '../utils/risk';
import { pipelineRunList } from '../api';
import { RunDetailPanel } from '../components/dashboard/RunDetailPanel';

export function WorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const { data: runs = [], isLoading, error } = useQuery({
    queryKey: ['pipelineRuns', workspaceId],
    queryFn: () => pipelineRunList(workspaceId!),
    enabled: !!workspaceId,
    refetchInterval: 30000,
  });

  const selectedRun = runs.find((r) => r.id === selectedRunId) || runs[0] || null;

  if (isLoading) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-copper border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center p-8">
          <svg className="w-16 h-16 text-fail mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h2 className="mt-4 text-2xl font-semibold text-paper mb-2">Failed to load workspace</h2>
          <p className="text-muted mb-6">Unable to load workspace data</p>
          <button
            onClick={() => window.location.reload()}
            className="rounded-md bg-copper px-4 py-2 text-sm font-semibold text-ink hover:brightness-110"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-ink">
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-8">
        {/* Header */}
        <div className="mb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div>
            <p className="text-muted text-sm mb-1">Workspace</p>
            <h1 className="text-3xl font-semibold tracking-tight">Workspace Detail</h1>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              className="inline-flex items-center gap-2 whitespace-nowrap rounded-md border border-line bg-ink px-4 py-2 text-sm font-medium text-muted transition-colors duration-150 hover:border-copper hover:text-paper"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <>
            {/* Main - Pipeline Runs */}
            <div className="min-w-0">
              <div className="overflow-hidden rounded-lg border border-line bg-ink-900">
                <div className="flex items-center justify-between border-b border-line px-4 py-3">
                  <h2 className="text-lg font-semibold">Pipeline Runs</h2>
                  <div className="flex items-center gap-2 text-sm text-muted">
                    <span className="font-mono">{runs.length}</span>
                    <span className="text-muted">runs</span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-[13px]">
                    <thead>
                      <tr className="text-left text-[12px] text-muted border-b border-line">
                        <th className="py-2.5 pr-3 font-normal w-[20%]">Run</th>
                        <th className="py-2.5 pr-3 font-normal w-[20%]">Branch</th>
                        <th className="py-2.5 pr-3 font-normal w-[15%]">Status</th>
                        <th className="py-2.5 pr-3 font-normal w-[15%]">Risk</th>
                        <th className="py-2.5 pr-3 font-normal w-[15%]">Action</th>
                        <th className="py-2.5 pr-3 font-normal text-right w-[20%]">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-12 text-center text-muted">
                            No pipeline runs yet. Push to a connected repository to see runs here.
                          </td>
                        </tr>
                      ) : (
                        runs.map((run) => {
                          return (
                            <tr
                              key={run.id}
                              onClick={() => setSelectedRunId(run.id)}
                              className={`cursor-pointer border-t border-line transition-colors duration-150 ${
                                selectedRunId === run.id ? 'bg-ink-700' : 'hover:bg-ink-800'
                              }`}
                            >
                              <td className="py-2.5 pr-3">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedRunId(run.id);
                                  }}
                                  className="whitespace-nowrap rounded-sm font-mono text-paper"
                                >
                                  #{run.run_id}
                                </button>
                                <div className="text-[12px] text-muted">{workspaceId}</div>
                              </td>
                              <td className="py-2.5 pr-3 font-mono text-[12px] text-paper/90 max-w-[180px] truncate">
                                {run.branch || '—'}
                              </td>
                              <td className="py-2.5 pr-3">
                                <span className={`inline-block whitespace-nowrap rounded-sm px-1.5 py-px font-mono text-[11px] ${
                                  run.conclusion === 'success' ? 'bg-fix/20 text-fix border border-fix/30' :
                                  run.conclusion === 'failure' ? 'bg-fail/20 text-fail-soft border border-fail/30' :
                                  'bg-copper/20 text-copper border border-copper/30'
                                }`}>
                                  {run.conclusion || run.workflow_status || '—'}
                                </span>
                              </td>
                              <td className="py-2.5 pr-3 text-right">
                                <span className={`font-mono ${riskTextClass(run.risk_score || 0)}`}>
                                  {run.risk_score ?? '—'}
                                </span>
                              </td>
                              <td className="py-2.5 pr-3 text-right">
                                {run.autofix_mode && (
                                  <span className={`inline-block whitespace-nowrap rounded-sm border px-1.5 py-px font-mono text-[11px] ${
                                    run.autofix_mode === 'auto_fix' ? 'bg-teal text-paper border-teal' :
                                    run.autofix_mode === 'approval_required' ? 'border-copper text-copper' :
                                    'border-fail text-fail-soft'
                                  }`}>
                                    {run.autofix_mode === 'auto_fix' ? 'Auto-fix' :
                                     run.autofix_mode === 'approval_required' ? 'Approval' : 'Blocked'}
                                  </span>
                                )}
                              </td>
                              <td className="py-2.5 pr-3 text-right font-mono text-[12px] text-muted">
                                {run.created_at ? new Date(run.created_at).toLocaleString() : '—'}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Detail Panel */}
            <div className="hidden border-l border-line bg-ink-800/60 p-5 lg:block" aria-label="Run detail">
              {selectedRun ? (
                <RunDetailPanel run={selectedRun} onClose={() => setSelectedRunId(null)} />
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted">
                  <svg className="w-16 h-16 mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V21a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  </svg>
                  <p className="text-center">Select a run to see details</p>
                </div>
              )}
            </div>
          </>
        </div>
      </div>
    </div>
  );
}