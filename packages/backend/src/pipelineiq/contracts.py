from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskBand(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PolicyAction(StrEnum):
    AUTO_FIX = "auto_fix"
    APPROVAL_REQUIRED = "approval_required"
    BLOCK_ONLY = "block_only"


class RiskProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    production_branch: str = Field(default="main", min_length=1, max_length=50)
    require_approval_above: int = Field(default=60, ge=0, le=100)
    auto_fix_below: int = Field(default=30, ge=0, le=100)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "RiskProfile":
        if self.auto_fix_below > self.require_approval_above:
            raise ValueError("auto_fix_below must be <= require_approval_above")
        return self


class RiskSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch: str = Field(min_length=1, max_length=255)
    files_changed: int = Field(default=0, ge=0)
    lines_changed: int = Field(default=0, ge=0)
    touches_sensitive_files: bool = False
    tests_failed: bool = True
    has_required_review: bool = False
    prior_similar_failures: int = Field(default=0, ge=0)


class RiskAssessmentRequest(BaseModel):
    signals: RiskSignals
    profile: RiskProfile = Field(default_factory=RiskProfile)


class RiskFactor(BaseModel):
    name: str
    points: int
    reason: str


class RiskAssessment(BaseModel):
    score: int = Field(ge=0, le=100)
    band: RiskBand
    action: PolicyAction
    factors: list[RiskFactor]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    risk_profile: RiskProfile | None = None
    slack_devops_mention: str | None = Field(default=None, max_length=100)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    owner_id: str
    github_installation_id: int | None = None
    github_repository_id: int | None = None
    github_repo_full_name: str | None = None
    github_default_branch: str | None = None
    github_repo_private: bool | None = None
    github_repo_html_url: str | None = None
    github_account_login: str | None = None
    github_account_type: str | None = None
    slack_devops_mention: str | None = None
    risk_profile: RiskProfile
    connected_at: str | None = None
    last_webhook_event_at: str | None = None
    created_at: str
    updated_at: str
    connected: bool


class RepositoryCreate(BaseModel):
    github_repo_id: int = Field(gt=0)
    full_name: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    private: bool = False
    html_url: str
    default_branch: str = Field(default="main", min_length=1, max_length=255)


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    github_repo_id: int
    full_name: str
    name: str
    private: bool
    html_url: str
    default_branch: str
    workspace_id: str
    connected_at: str
    connected_by: str


class WebhookEventResponse(BaseModel):
    delivery_id: str
    event_type: str
    action: str | None = None
    repository_full_name: str | None = None
    received_at: str


class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    installation_id: int | None = None
    repository_full_name: str
    delivery_id: str
    event_type: str
    action: str | None = None
    run_id: int | None = None
    workflow_status: str | None = None
    workflow_name: str | None = None
    workflow_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    triggered_by: str | None = None
    conclusion: str | None = None
    health_status: str
    monitor_status: str
    diagnosis_status: str
    risk_status: str
    monitor_summary: str | None = None
    monitor_report_json: dict[str, Any]
    monitor_logs_excerpt: list[str]
    diagnosis_report: str | None = None
    diagnosis_report_json: dict[str, Any]
    diagnosis_error: str | None = None
    risk_score: int | None = None
    risk_band: str | None = None
    risk_report_json: dict[str, Any]
    risk_inputs_json: dict[str, Any]
    risk_error: str | None = None
    risk_provider: str | None = None
    risk_model: str | None = None
    autofix_status: str
    autofix_mode: str | None = None
    autofix_report_url: str | None = None
    autofix_pr_url: str | None = None
    autofix_execution_id: str | None = None
    autofix_error: str | None = None
    autofix_feedback_url: str | None = None
    autofix_feedback_status: str | None = None
    error_summary: str | None = None
    diagnosis_provider: str | None = None
    diagnosis_model: str | None = None
    monitor_provider: str | None = None
    monitor_model: str | None = None
    raw_event: dict[str, Any]
    enriched_event: dict[str, Any]
    created_at: str
    updated_at: str


class AutoFixExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    pipeline_run_id: str
    repository_full_name: str
    target_branch: str
    error_signature: str
    risk_score: int
    policy_action: str
    execution_status: str
    reviewer_username: str | None = None
    reviewer_github_id: int | None = None
    mode: str
    proposed_fix_json: dict[str, Any]
    report_json: dict[str, Any]
    pr_number: int | None = None
    pr_url: str | None = None
    pr_state: str | None = None
    fix_branch: str | None = None
    merge_sha: str | None = None
    loop_blocked_reason: str | None = None
    signed_report_token: str | None = None
    report_feedback_status: str | None = None
    report_feedback_note: str | None = None
    resolution_feedback_status: str | None = None
    resolution_feedback_url: str | None = None
    resolution_feedback_requested_at: str | None = None
    resolution_feedback_submitted_at: str | None = None
    created_at: str
    updated_at: str


class AutoFixFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    execution_id: str
    pipeline_run_id: str
    repository_full_name: str
    error_signature: str
    target_branch: str
    reviewer_username: str | None = None
    reviewer_github_id: int | None = None
    feedback_token: str
    feedback_url: str
    status: str
    outcome: str | None = None
    automation_quality: str | None = None
    should_auto_apply_similar: bool | None = None
    notes: str | None = None
    requested_at: str
    submitted_at: str | None = None
    created_at: str
    updated_at: str


class AutoFixMemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    repository_full_name: str
    error_signature: str
    memory_type: str
    reviewer_username: str | None = None
    reviewer_github_id: int | None = None
    note: str | None = None
    approved_for_auto_merge: bool
    created_at: str
    updated_at: str


class AutoFixReportResponse(BaseModel):
    execution: AutoFixExecutionResponse
    pipeline_run: PipelineRunResponse


class AutoFixReportDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: str | None = Field(default=None, max_length=500)


class AutoFixFeedbackRequest(BaseModel):
    outcome: str = Field(pattern="^(resolved|partially_resolved|not_resolved)$")
    automation_quality: str = Field(pattern="^(excellent|acceptable|poor)$")
    should_auto_apply_similar: bool
    notes: str | None = Field(default=None, max_length=1000)


class DiagnosisResponse(BaseModel):
    error_type: str
    possible_causes: list[str]
    latest_working_change: str
    suggested_fixes: list[str]
    provider: str
    model: str
    raw_response: str


class WorkspaceParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    role: str
    joined_at: str
    last_active_at: str
    presence: dict[str, Any]


class CollaborativeWorkspaceCreate(BaseModel):
    incident_id: str
    repository_full_name: str
    base_branch: str
    head_branch: str
    head_sha: str


class CollaborativeWorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    workspace_id: str
    repository_full_name: str
    base_branch: str
    head_branch: str
    head_sha: str
    owner_id: str
    participants: list[WorkspaceParticipantResponse]
    status: str
    created_at: str
    updated_at: str
    last_synced_at: str | None = None


class WorkspaceDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    path: str
    language: str
    content: str
    original_content: str
    version: int
    last_modified_by: str
    last_modified_at: str
    is_binary: bool


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    document_id: str
    version_number: int
    parent_version_id: str | None = None
    content_snapshot: str
    operations: list[dict[str, Any]]
    author_id: str
    author_type: str
    message: str
    tags: list[str]
    ci_run_id: str | None = None
    ci_status: str | None = None
    ci_url: str | None = None
    created_at: str


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    workspace_id: str
    actor_id: str
    actor_type: str
    actor_name: str
    type: str
    action: str
    description: str
    document_id: str | None = None
    version_id: str | None = None
    before: dict[str, Any]
    after: dict[str, Any]
    metadata: dict[str, Any]
    correlation_id: str | None = None
    causation_id: str | None = None
    timestamp: str


class ValidationStageResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    status: str
    command: str
    output: str | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class ValidationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    version_id: str
    triggered_by: str
    status: str
    stages: list[ValidationStageResultResponse]
    started_at: str | None = None
    completed_at: str | None = None
    logs: list[str]
    created_at: str


class CreateCheckpointRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list)


class RestoreVersionRequest(BaseModel):
    version_id: str


class AuditEventFilter(BaseModel):
    actor_type: str | None = None
    event_type: str | None = None
    actor_id: str | None = None
    document_id: str | None = None
    from_timestamp: str | None = None
    to_timestamp: str | None = None
    limit: int = Field(default=100, ge=1, le=500)


class AuditEventSummary(BaseModel):
    total_events: int
    actor_type_breakdown: dict[str, int]
    event_type_breakdown: dict[str, int]
    time_range: dict[str, str | None]
