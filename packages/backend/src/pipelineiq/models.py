from datetime import UTC, datetime
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from pipelineiq.contracts import RiskProfile


def utc_now() -> datetime:
    return datetime.now(UTC)


class GitHubOrganization(BaseModel):
    id: int
    login: str
    avatar_url: str | None = None
    description: str | None = None
    url: str | None = None


class User(Document):
    github_id: int
    username: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    github_access_token: str
    organizations: list[GitHubOrganization] = Field(default_factory=list)
    last_login: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    is_active: bool = True

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            IndexModel([("github_id", ASCENDING)], unique=True),
            "username",
            IndexModel([("email", ASCENDING)], sparse=True),
            "is_active",
        ]


class Workspace(Document):
    name: str
    description: str | None = None
    owner_id: PydanticObjectId
    github_installation_id: int | None = None
    github_repository_id: int | None = None
    github_repo_full_name: str | None = None
    github_default_branch: str | None = None
    github_repo_private: bool | None = None
    github_repo_html_url: str | None = None
    github_account_login: str | None = None
    github_account_type: str | None = None
    slack_devops_mention: str | None = None
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)
    connected_at: datetime | None = None
    last_webhook_event_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "workspaces"
        use_state_management = True
        indexes = [
            "owner_id",
            IndexModel([("github_installation_id", ASCENDING)], unique=True, sparse=True),
            IndexModel([("github_repository_id", ASCENDING)], sparse=True),
            IndexModel([("created_at", DESCENDING)]),
        ]


class Repository(Document):
    github_repo_id: int
    full_name: str
    name: str
    private: bool = False
    html_url: str
    default_branch: str = "main"
    workspace_id: PydanticObjectId
    connected_at: datetime = Field(default_factory=utc_now)
    connected_by: PydanticObjectId

    class Settings:
        name = "repositories"
        use_state_management = True
        indexes = [
            "workspace_id",
            IndexModel([("github_repo_id", ASCENDING)], unique=True),
            "full_name",
        ]


class WebhookEvent(Document):
    delivery_id: str
    event_type: str
    action: str | None = None
    installation_id: int | None = None
    repository_full_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "webhook_events"
        use_state_management = True
        indexes = [
            IndexModel([("delivery_id", ASCENDING)], unique=True),
            IndexModel([("installation_id", ASCENDING), ("received_at", DESCENDING)]),
            IndexModel([("event_type", ASCENDING), ("received_at", DESCENDING)]),
            IndexModel([("received_at", DESCENDING)], expireAfterSeconds=2_592_000),
        ]


class PipelineRun(Document):
    workspace_id: PydanticObjectId
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
    health_status: str = "unknown"
    kafka_status: str = "disabled"
    monitor_status: str = "pending"
    diagnosis_status: str = "pending"
    risk_status: str = "pending"
    monitor_summary: str | None = None
    monitor_report_json: dict[str, Any] = Field(default_factory=dict)
    monitor_logs_excerpt: list[str] = Field(default_factory=list)
    diagnosis_report: str | None = None
    diagnosis_report_json: dict[str, Any] = Field(default_factory=dict)
    diagnosis_error: str | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)
    risk_band: str | None = None
    risk_report_json: dict[str, Any] = Field(default_factory=dict)
    risk_inputs_json: dict[str, Any] = Field(default_factory=dict)
    risk_error: str | None = None
    risk_provider: str | None = None
    risk_model: str | None = None
    autofix_status: str = "pending"
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
    raw_event: dict[str, Any] = Field(default_factory=dict)
    enriched_event: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "pipeline_runs"
        use_state_management = True
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("delivery_id", ASCENDING)], unique=True),
            IndexModel([("run_id", ASCENDING)], sparse=True),
            "health_status",
            "monitor_status",
            "diagnosis_status",
            "risk_status",
            "autofix_status",
            "branch",
            "commit_sha",
            IndexModel([("created_at", DESCENDING)], expireAfterSeconds=31_536_000),
        ]


class AutoFixExecution(Document):
    workspace_id: PydanticObjectId
    pipeline_run_id: PydanticObjectId
    repository_full_name: str
    target_branch: str
    error_signature: str
    risk_score: int = Field(ge=0, le=100)
    policy_action: str
    execution_status: str = "pending"
    reviewer_username: str | None = None
    reviewer_github_id: int | None = None
    mode: str = "report_only"
    proposed_fix_json: dict[str, Any] = Field(default_factory=dict)
    report_json: dict[str, Any] = Field(default_factory=dict)
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
    resolution_feedback_requested_at: datetime | None = None
    resolution_feedback_submitted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "autofix_executions"
        use_state_management = True
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("pipeline_run_id", ASCENDING)], unique=True),
            IndexModel([("signed_report_token", ASCENDING)], unique=True, sparse=True),
            "execution_status",
            "error_signature",
        ]


class AutoFixFeedback(Document):
    workspace_id: PydanticObjectId
    execution_id: PydanticObjectId
    pipeline_run_id: PydanticObjectId
    repository_full_name: str
    error_signature: str
    target_branch: str
    reviewer_username: str | None = None
    reviewer_github_id: int | None = None
    feedback_token: str
    feedback_url: str
    status: str = "requested"
    outcome: str | None = None
    automation_quality: str | None = None
    should_auto_apply_similar: bool | None = None
    notes: str | None = None
    requested_at: datetime = Field(default_factory=utc_now)
    submitted_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "autofix_feedbacks"
        use_state_management = True
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("execution_id", ASCENDING)], unique=True),
            IndexModel([("feedback_token", ASCENDING)], unique=True),
            "status",
            "error_signature",
        ]


class AutoFixMemory(Document):
    workspace_id: PydanticObjectId
    repository_full_name: str
    error_signature: str
    memory_type: str
    reviewer_username: str | None = None
    reviewer_github_id: int | None = None
    note: str | None = None
    approved_for_auto_merge: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "autofix_memories"
        use_state_management = True
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("error_signature", ASCENDING)], unique=True),
            IndexModel([("repository_full_name", ASCENDING), ("error_signature", ASCENDING)]),
            "approved_for_auto_merge",
        ]


class WorkspaceParticipant(BaseModel):
    user_id: PydanticObjectId
    role: str = "editor"  # owner, editor, reviewer, viewer
    joined_at: datetime = Field(default_factory=utc_now)
    last_active_at: datetime = Field(default_factory=utc_now)
    presence: dict[str, Any] = Field(default_factory=dict)


class CollaborativeWorkspace(Document):
    incident_id: PydanticObjectId
    workspace_id: str  # UUID for frontend
    repository_full_name: str
    base_branch: str
    head_branch: str
    head_sha: str
    owner_id: PydanticObjectId
    participants: list[WorkspaceParticipant] = Field(default_factory=list)
    status: str = (
        "initializing"  # initializing, active, validating, awaiting_approval, resolved, closed
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_synced_at: datetime | None = None

    class Settings:
        name = "collaborative_workspaces"
        use_state_management = True
        indexes = [
            "incident_id",
            "owner_id",
            "status",
            IndexModel([("updated_at", DESCENDING)]),
        ]


class WorkspaceDocument(Document):
    workspace_id: PydanticObjectId
    path: str
    language: str
    content: str  # Current Yjs state (base64 encoded)
    original_content: str
    version: int = 0
    last_modified_by: PydanticObjectId
    last_modified_at: datetime = Field(default_factory=utc_now)
    is_binary: bool = False
    yjs_state: bytes | None = None  # Binary Yjs document state

    class Settings:
        name = "workspace_documents"
        use_state_management = True
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("path", ASCENDING)], unique=True),
        ]


class DocumentVersion(Document):
    workspace_id: PydanticObjectId
    document_id: PydanticObjectId
    version_number: int
    parent_version_id: PydanticObjectId | None = None
    content_snapshot: str
    operations: list[dict[str, Any]] = Field(default_factory=list)
    author_id: PydanticObjectId
    author_type: str  # human, ai, system
    message: str
    tags: list[str] = Field(default_factory=list)
    ci_run_id: PydanticObjectId | None = None
    ci_status: str | None = None
    ci_url: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "document_versions"
        use_state_management = True
        indexes = [
            IndexModel(
                [
                    ("workspace_id", ASCENDING),
                    ("document_id", ASCENDING),
                    ("version_number", DESCENDING),
                ]
            ),
            "author_id",
            "tags",
        ]


class IncidentEvent(Document):
    incident_id: PydanticObjectId
    workspace_id: PydanticObjectId
    actor_id: PydanticObjectId
    actor_type: str  # human, ai, system, webhook
    actor_name: str
    type: str
    action: str
    description: str
    document_id: PydanticObjectId | None = None
    version_id: PydanticObjectId | None = None
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "incident_events"
        use_state_management = True
        indexes = [
            IndexModel([("incident_id", ASCENDING), ("timestamp", ASCENDING)]),
            IndexModel([("workspace_id", ASCENDING), ("timestamp", DESCENDING)]),
            "actor_id",
            "actor_type",
            "type",
        ]


class ValidationRun(Document):
    workspace_id: PydanticObjectId
    version_id: PydanticObjectId
    triggered_by: PydanticObjectId
    status: str = "pending"  # pending, running, passed, failed
    stages: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    logs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "validation_runs"
        use_state_management = True
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", DESCENDING)]),
            "version_id",
            "status",
        ]


DOCUMENT_MODELS = [
    User,
    Workspace,
    Repository,
    WebhookEvent,
    PipelineRun,
    AutoFixExecution,
    AutoFixFeedback,
    AutoFixMemory,
    CollaborativeWorkspace,
    WorkspaceDocument,
    DocumentVersion,
    IncidentEvent,
    ValidationRun,
]
