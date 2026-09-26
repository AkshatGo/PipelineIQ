export enum HealthStatus {
  Unknown = "unknown",
  Healthy = "healthy",
  Failed = "failed",
}

export enum ProcessingStatus {
  Pending = "pending",
  Running = "running",
  Completed = "completed",
  Failed = "failed",
}

export type RiskBand = "low" | "medium" | "high";
export type PolicyAction = "auto_fix" | "approval_required" | "block_only";

export interface RiskProfile {
  production_branch: string;
  require_approval_above: number;
  auto_fix_below: number;
}

export interface RiskSignals {
  branch: string;
  files_changed: number;
  lines_changed: number;
  touches_sensitive_files: boolean;
  tests_failed: boolean;
  has_required_review: boolean;
  prior_similar_failures: number;
}

export interface RiskAssessmentRequest {
  signals: RiskSignals;
  profile?: RiskProfile;
}

export interface RiskFactor {
  name: string;
  points: number;
  reason: string;
}

export interface RiskAssessment {
  score: number;
  band: RiskBand;
  action: PolicyAction;
  factors: RiskFactor[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export interface GitHubWebhookReceipt {
  received: boolean;
  event_type: string;
  delivery_id: string;
  ignored?: string;
  duplicate: boolean;
  workspace_id?: string;
  repo?: string;
  run_id?: number;
  conclusion?: string;
  branch?: string;
  commit_sha?: string;
  triggered_by?: string;
  kafka_topic?: string;
}

export interface GitHubOrganization {
  id: number;
  login: string;
  avatar_url?: string;
  description?: string;
  url?: string;
}

export interface UserResponse {
  id: string;
  github_id: number;
  username: string;
  display_name?: string;
  email?: string;
  avatar_url?: string;
  organizations: GitHubOrganization[];
  last_login: string;
  created_at: string;
}

export interface WorkspaceResponse {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  github_repo_full_name?: string;
  risk_profile: RiskProfile;
  connected: boolean;
  created_at: string;
  updated_at: string;
}
