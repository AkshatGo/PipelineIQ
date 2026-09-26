import { api } from "./client";
import type { WorkspaceResponse, WorkspaceCreate, WorkspaceUpdate, RepositoryResponse, WebhookEventResponse } from "@pipelineiq/shared";

export async function workspaceList(): Promise<WorkspaceResponse[]> {
  const response = await api.get<WorkspaceResponse[]>("/api/workspaces");
  return response.data;
}

export async function workspaceCreate(payload: WorkspaceCreate): Promise<WorkspaceResponse> {
  const response = await api.post<WorkspaceResponse>("/api/workspaces", payload);
  return response.data;
}

export async function workspaceGet(workspaceId: string): Promise<WorkspaceResponse> {
  const response = await api.get<WorkspaceResponse>(`/api/workspaces/${workspaceId}`);
  return response.data;
}

export async function workspaceUpdate(workspaceId: string, payload: WorkspaceUpdate): Promise<WorkspaceResponse> {
  const response = await api.patch<WorkspaceResponse>(`/api/workspaces/${workspaceId}`, payload);
  return response.data;
}

export async function workspaceDelete(workspaceId: string): Promise<{ detail: string }> {
  const response = await api.delete(`/api/workspaces/${workspaceId}`);
  return response.data;
}

export async function repositoryList(workspaceId: string): Promise<RepositoryResponse[]> {
  const response = await api.get<RepositoryResponse[]>(`/api/workspaces/${workspaceId}/repositories`);
  return response.data;
}

export async function repositoryCreate(workspaceId: string, payload: { github_repo_id: number; full_name: string; name: string; private: boolean; html_url: string; default_branch: string }): Promise<RepositoryResponse> {
  const response = await api.post<RepositoryResponse>(`/api/workspaces/${workspaceId}/repositories`, payload);
  return response.data;
}

export async function repositoryDelete(workspaceId: string, repoId: string): Promise<{ detail: string }> {
  const response = await api.delete(`/api/workspaces/${workspaceId}/repositories/${repoId}`);
  return response.data;
}

export async function githubAppInstall(workspaceId: string): Promise<{ install_url: string }> {
  const response = await api.get(`/api/workspaces/${workspaceId}/github/install`);
  return response.data;
}

export async function githubAppDisconnect(workspaceId: string): Promise<{ detail: string }> {
  const response = await api.delete(`/api/workspaces/${workspaceId}/github/installation`);
  return response.data;
}

export async function webhookEvents(workspaceId: string, limit: number = 10): Promise<WebhookEventResponse[]> {
  const response = await api.get<WebhookEventResponse[]>(`/api/workspaces/${workspaceId}/github/events`, { params: { limit } });
  return response.data;
}