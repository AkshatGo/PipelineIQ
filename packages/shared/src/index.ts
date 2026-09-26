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

export interface WorkspaceCreate {
  name: string;
  description?: string;
  risk_profile?: RiskProfile;
}

export interface WorkspaceUpdate {
  name?: string;
  description?: string;
  risk_profile?: RiskProfile;
  slack_devops_mention?: string;
}

export interface WorkspaceResponse {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  github_installation_id?: number;
  github_repository_id?: number;
  github_repo_full_name?: string;
  github_default_branch?: string;
  github_repo_private?: boolean;
  github_repo_html_url?: string;
  github_account_login?: string;
  github_account_type?: string;
  slack_devops_mention?: string;
  risk_profile: RiskProfile;
  connected_at?: string;
  last_webhook_event_at?: string;
  created_at: string;
  updated_at: string;
  connected: boolean;
}

export interface RepositoryCreate {
  github_repo_id: number;
  full_name: string;
  name: string;
  private: boolean;
  html_url: string;
  default_branch: string;
}

export interface RepositoryResponse {
  id: string;
  github_repo_id: number;
  full_name: string;
  name: string;
  private: boolean;
  html_url: string;
  default_branch: string;
  workspace_id: string;
  connected_at: string;
  connected_by: string;
}

export interface WebhookEventResponse {
  delivery_id: string;
  event_type: string;
  action?: string;
  repository_full_name?: string;
  received_at: string;
}

export interface PipelineRunResponse {
  id: string;
  workspace_id: string;
  installation_id?: number;
  repository_full_name: string;
  delivery_id: string;
  event_type: string;
  action?: string;
  run_id?: number;
  workflow_status?: string;
  workflow_name?: string;
  workflow_url?: string;
  branch?: string;
  commit_sha?: string;
  triggered_by?: string;
  conclusion?: string;
  health_status: string;
  monitor_status: string;
  diagnosis_status: string;
  risk_status: string;
  monitor_summary?: string;
  monitor_report_json: Record<string, any>;
  monitor_logs_excerpt: string[];
  diagnosis_report?: string;
  diagnosis_report_json: Record<string, any>;
  diagnosis_error?: string;
  risk_score?: number;
  risk_band?: string;
  risk_report_json: Record<string, any>;
  risk_inputs_json: Record<string, any>;
  risk_error?: string;
  risk_provider?: string;
  risk_model?: string;
  autofix_status: string;
  autofix_mode?: string;
  autofix_report_url?: string;
  autofix_pr_url?: string;
  autofix_execution_id?: string;
  autofix_error?: string;
  autofix_feedback_url?: string;
  autofix_feedback_status?: string;
  error_summary?: string;
  diagnosis_provider?: string;
  diagnosis_model?: string;
  monitor_provider?: string;
  monitor_model?: string;
  raw_event: Record<string, any>;
  enriched_event: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AutoFixExecutionResponse {
  id: string;
  workspace_id: string;
  pipeline_run_id: string;
  repository_full_name: string;
  target_branch: string;
  error_signature: string;
  risk_score: number;
  policy_action: string;
  execution_status: string;
  reviewer_username?: string;
  reviewer_github_id?: number;
  mode: string;
  proposed_fix_json: Record<string, any>;
  report_json: Record<string, any>;
  pr_number?: number;
  pr_url?: string;
  pr_state?: string;
  fix_branch?: string;
  merge_sha?: string;
  loop_blocked_reason?: string;
  signed_report_token?: string;
  report_feedback_status?: string;
  report_feedback_note?: string;
  resolution_feedback_status?: string;
  resolution_feedback_url?: string;
  resolution_feedback_requested_at?: string;
  resolution_feedback_submitted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface AutoFixFeedbackResponse {
  id: string;
  workspace_id: string;
  execution_id: string;
  pipeline_run_id: string;
  repository_full_name: string;
  error_signature: string;
  target_branch: string;
  reviewer_username?: string;
  reviewer_github_id?: number;
  feedback_token: string;
  feedback_url: string;
  status: string;
  outcome?: string;
  automation_quality?: string;
  should_auto_apply_similar?: boolean;
  notes?: string;
  requested_at: string;
  submitted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface AutoFixMemoryResponse {
  id: string;
  workspace_id: string;
  repository_full_name: string;
  error_signature: string;
  memory_type: string;
  reviewer_username?: string;
  reviewer_github_id?: number;
  note?: string;
  approved_for_auto_merge: boolean;
  created_at: string;
  updated_at: string;
}

export interface AutoFixReportResponse {
  execution: AutoFixExecutionResponse;
  pipeline_run: PipelineRunResponse;
}

export interface AutoFixReportDecisionRequest {
  decision: "approve" | "reject";
  note?: string;
}

export interface AutoFixFeedbackRequest {
  outcome: "resolved" | "partially_resolved" | "not_resolved";
  automation_quality: "excellent" | "acceptable" | "poor";
  should_auto_apply_similar: boolean;
  notes?: string;
}

export interface DiagnosisResponse {
  error_type: string;
  possible_causes: string[];
  latest_working_change: string;
  suggested_fixes: string[];
  provider: string;
  model: string;
  raw_response: string;
}