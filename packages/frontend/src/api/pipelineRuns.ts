import { api } from "./client";
import type { PipelineRunResponse } from "@pipelineiq/shared";

export async function pipelineRunList(workspaceId: string): Promise<PipelineRunResponse[]> {
  const response = await api.get<PipelineRunResponse[]>(`/api/workspaces/${workspaceId}/pipeline-runs`);
  return response.data;
}

export async function pipelineRunGet(workspaceId: string, runId: string): Promise<PipelineRunResponse> {
  const response = await api.get<PipelineRunResponse>(`/api/workspaces/${workspaceId}/pipeline-runs/${runId}`);
  return response.data;
}