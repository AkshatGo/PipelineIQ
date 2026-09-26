import type { RiskAssessment, RiskAssessmentRequest } from "@pipelineiq/shared";

import { api } from "./client";

export async function assessRisk(payload: RiskAssessmentRequest): Promise<RiskAssessment> {
  const response = await api.post<RiskAssessment>("/risk/assess", payload);
  return response.data;
}

