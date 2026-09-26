import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FolderGitIcon, AlertTriangleIcon } from 'lucide-react';
import { ConnectButton } from '../components/ConnectButton';
import { Logo } from '../components/Logo';
import { workspaceList, workspaceCreate, workspaceDelete } from '../api';
import type { WorkspaceResponse, WorkspaceCreate } from "@pipelineiq/shared";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState('');

  const { data: workspaces = [], isLoading, error } = useQuery({
    queryKey: ['workspaces'],
    queryFn: workspaceList,
  });

  const createMutation = useMutation({
    mutationFn: (payload: WorkspaceCreate) => workspaceCreate(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      setShowCreateModal(false);
      setNewWorkspaceName('');
      setNewWorkspaceDescription('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (workspaceId: string) => workspaceDelete(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    createMutation.mutate({
      name: newWorkspaceName.trim(),
      description: newWorkspaceDescription.trim() || undefined,
    });
  };

  const handleDelete = (workspaceId: string, name: string) => {
    if (!confirm(`Delete workspace "${name}"? This cannot be undone.`)) return;
    deleteMutation.mutate(workspaceId);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-copper border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted">Loading workspaces...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen w-full bg-ink flex items-center justify-center">
        <div className="text-center p-8">
          <AlertTriangleIcon className="w-16 h-16 text-fail mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-paper mb-2">Failed to load workspaces</h2>
          <p className="text-muted mb-6">{error instanceof Error ? error.message : 'Unknown error'}</p>
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
      <div className="mx-auto max-w-7xl px-5 py-8 md:px-8 lg:py-12">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Logo className="h-8 w-8" />
              <h1 className="text-3xl font-semibold tracking-tight">Workspaces</h1>
            </div>
            <p className="text-muted">
              Manage your repositories and monitor pipeline health
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-md bg-signal px-5 py-3 text-[16px] font-semibold text-ink transition-[filter,transform] duration-150 ease-out hover:brightness-110 active:scale-[0.98]"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Workspace
          </button>
        </div>

        {workspaces.length === 0 ? (
          <div className="text-center py-16">
            <svg className="mx-auto h-16 w-16 text-muted/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <h3 className="mt-4 text-xl font-semibold text-paper">No workspaces yet</h3>
            <p className="mt-2 text-muted max-w-md mx-auto">
              Connect a GitHub repository to start monitoring your CI/CD pipelines
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-6 inline-flex items-center gap-2 whitespace-nowrap rounded-md bg-signal px-5 py-3 text-[16px] font-semibold text-ink transition-[filter,transform] duration-150 ease-out hover:brightness-110 active:scale-[0.98]"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create Your First Workspace
            </button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {workspaces.map((workspace) => (
              <WorkspaceCard
                key={workspace.id}
                workspace={workspace}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}

        {/* Create Workspace Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-ink-900 rounded-lg border border-line p-6 animate-in">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">Create Workspace</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-muted hover:text-paper transition-colors"
                >
                  ✕
                </button>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-muted mb-1.5">
                    Workspace Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    value={newWorkspaceName}
                    onChange={(e) => setNewWorkspaceName(e.target.value)}
                    placeholder="e.g., checkout-api"
                    className="w-full rounded-md border border-line bg-ink px-4 py-2.5 text-paper placeholder-muted focus:border-copper focus:outline-none focus:ring-2 focus:ring-copper/20"
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-muted mb-1.5">
                    Description (optional)
                  </label>
                  <textarea
                    id="description"
                    value={newWorkspaceDescription}
                    onChange={(e) => setNewWorkspaceDescription(e.target.value)}
                    placeholder="e.g., Main checkout service"
                    rows={3}
                    className="w-full rounded-md border border-line bg-ink px-4 py-2.5 text-paper placeholder-muted focus:border-copper focus:outline-none focus:ring-2 focus:ring-copper/20 resize-none"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 rounded-md border border-line bg-ink px-4 py-2.5 text-sm font-medium text-paper hover:bg-ink-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!newWorkspaceName.trim()}
                    className="flex-1 rounded-md bg-signal px-4 py-2.5 text-sm font-semibold text-ink hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Create Workspace
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface WorkspaceCardProps {
  workspace: WorkspaceResponse;
  onDelete: (id: string, name: string) => void;
}

function WorkspaceCard({ workspace, onDelete }: WorkspaceCardProps) {
  const statusConfig = {
    green: { dot: 'bg-fix', label: 'Healthy', text: 'text-fix' },
    red: { dot: 'bg-fail', label: 'Failing', text: 'text-fail' },
    fixing: { dot: 'bg-copper', label: 'Fixing', text: 'text-copper' },
  };

  const config = statusConfig[workspace.connected ? 'green' : 'red'];
  const lastEvent = workspace.last_webhook_event_at
    ? new Date(workspace.last_webhook_event_at).toLocaleDateString()
    : 'Never';

  return (
    <div className="relative group overflow-hidden rounded-lg border border-line bg-ink-900 p-5 transition-all duration-200 hover:border-copper/30 hover:shadow-[0_20px_40px_-20px_rgba(201,138,62,0.15)]">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <FolderGitIcon className="h-6 w-6 text-copper" />
          <div>
            <h3 className="font-semibold text-paper truncate">{workspace.name}</h3>
            {workspace.description && (
              <p className="text-sm text-muted truncate max-w-[200px]">{workspace.description}</p>
            )}
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(workspace.id, workspace.name);
          }}
          className="opacity-0 group-hover:opacity-100 text-muted hover:text-fail transition-all duration-200 p-1 rounded"
          aria-label={`Delete ${workspace.name}`}
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5.034 7" />
          </svg>
        </button>
      </div>

      <div className="flex items-center justify-between mb-4">
        <span className={`flex items-center gap-1.5 text-[13px] font-medium ${config.text}`}>
          <span className={`h-2 w-2 rounded-full ${config.dot}`} />
          {config.label}
        </span>
        <span className="text-[12px] text-muted">{lastEvent}</span>
      </div>

      <div className="border-t border-line pt-4">
        <div className="flex items-center justify-between text-xs text-muted mb-2">
          <span>Risk Score</span>
          <span className="font-mono font-medium">—</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span>Last Run</span>
          <span className="font-mono">—</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span>Auto-fix Rate</span>
          <span className="font-mono">—</span>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <a
          href={`/workspace/${workspace.id}`}
          className="flex-1 text-center rounded-md border border-line bg-ink px-3 py-2 text-sm font-medium text-muted hover:bg-ink-800 hover:text-paper transition-colors"
        >
          View Details
        </a>
        <ConnectButton
          href={`/api/workspaces/${workspace.id}/github/install`}
          label="Connect GitHub"
        />
      </div>
    </div>
  );
}