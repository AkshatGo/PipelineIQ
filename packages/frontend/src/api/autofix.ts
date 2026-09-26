import { api } from "./client";
import type { AutoFixReportResponse, AutoFixFeedbackResponse } from "@pipelineiq/shared";

export async function autofixReport(token: string): Promise<AutoFixReportResponse> {
  const response = await api.get<AutoFixReportResponse>(`/api/autofix/report`, { params: { token } });
  return response.data;
}

export async function autofixDecision(token: string, decision: "approve" | "reject", note?: string): Promise<{ detail: string; pr_url?: string; execution_status: string }> {
  const response = await api.post(`/api/autofix/report/decision`, { decision, note }, { params: { token } });
  return response.data;
}

export async function autofixFeedback(token: string): Promise<AutoFixFeedbackResponse> {
  const response = await api.get<AutoFixFeedbackResponse>(`/api/autofix/feedback`, { params: { token } });
  return response.data;
}

export async function autofixFeedbackSubmit(token: string, payload: { outcome: string; automation_quality: string; should_auto_apply_similar: boolean; notes?: string }): Promise<{ detail: string; feedback_id: string }> {
  const response = await api.post(`/api/autofix/feedback`, payload, { params: { token } });
  return response.data;
}