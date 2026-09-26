# Data Models Specification

## Overview

This document provides the complete specification for all MongoDB collections used in PipelineIQ, implemented as Beanie ODM documents with Pydantic v2 models.

---

## Collection: users

### Indexes
```javascript
db.users.createIndex({ "github_id": 1 }, { unique: true })
db.users.createIndex({ "username": 1 })
db.users.createIndex({ "email": 1 }, { sparse: true })
db.users.createIndex({ "is_active": 1 })
```

### Document Schema
```python
class GitHubOrganization(BaseModel):
    id: int
    login: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class User(Document):
    github_id: int                          # Unique GitHub user ID
    username: str                           # GitHub login
    display_name: Optional[str] = None      # GitHub name field
    email: Optional[str] = None             # Public email
    avatar_url: Optional[str] = None        # GitHub avatar URL
    github_access_token: str                # Encrypted OAuth token
    organizations: List[GitHubOrganization] = Field(default_factory=list)
    last_login: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    class Settings:
        name = "users"
        use_state_management = True
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d0"),
  "github_id": 583231,
  "username": "octocat",
  "display_name": "The Octocat",
  "email": "octocat@github.com",
  "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
  "github_access_token": "gho_encrypted_token_here",
  "organizations": [
    {
      "id": 9919,
      "login": "github",
      "avatar_url": "https://avatars.githubusercontent.com/u/9919?v=4",
      "description": "How people build software",
      "url": "https://api.github.com/orgs/github"
    }
  ],
  "last_login": ISODate("2026-09-26T12:00:00Z"),
  "created_at": ISODate("2026-01-15T10:00:00Z"),
  "is_active": true
}
```

---

## Collection: workspaces

### Indexes
```javascript
db.workspaces.createIndex({ "owner_id": 1 })
db.workspaces.createIndex({ "github_installation_id": 1 }, { unique: true, sparse: true })
db.workspaces.createIndex({ "github_repository_id": 1 }, { sparse: true })
db.workspaces.createIndex({ "created_at": -1 })
```

### Document Schema
```python
class RiskProfile(BaseModel):
    production_branch: str = "main"
    require_approval_above: int = Field(default=60, ge=0, le=100)
    auto_fix_below: int = Field(default=30, ge=0, le=100)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.auto_fix_below > self.require_approval_above:
            raise ValueError("auto_fix_below must be <= require_approval_above")
        return self


class Workspace(Document):
    name: str
    description: Optional[str] = None
    owner_id: PydanticObjectId
    github_installation_id: Optional[int] = None
    github_repository_id: Optional[int] = None
    github_repo_full_name: Optional[str] = None
    github_default_branch: Optional[str] = None
    github_repo_private: Optional[bool] = None
    github_repo_html_url: Optional[str] = None
    github_account_login: Optional[str] = None
    github_account_type: Optional[str] = None  # "User" or "Organization"
    slack_devops_mention: Optional[str] = None
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)
    connected_at: Optional[datetime] = None
    last_webhook_event_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workspaces"
        use_state_management = True
```

### Computed Properties (Not Stored)
```python
@property
def connected(self) -> bool:
    return self.github_installation_id is not None
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
  "name": "Production Pipeline",
  "description": "Main CI/CD monitoring for production services",
  "owner_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d0"),
  "github_installation_id": 12345678,
  "github_repository_id": 987654321,
  "github_repo_full_name": "myorg/myapp",
  "github_default_branch": "main",
  "github_repo_private": true,
  "github_repo_html_url": "https://github.com/myorg/myapp",
  "github_account_login": "myorg",
  "github_account_type": "Organization",
  "slack_devops_mention": "@devops-oncall",
  "risk_profile": {
    "production_branch": "main",
    "require_approval_above": 60,
    "auto_fix_below": 30
  },
  "connected_at": ISODate("2026-09-01T10:00:00Z"),
  "last_webhook_event_at": ISODate("2026-09-26T08:30:00Z"),
  "created_at": ISODate("2026-09-01T10:00:00Z"),
  "updated_at": ISODate("2026-09-26T08:30:00Z")
}
```

---

## Collection: repositories

### Indexes
```javascript
db.repositories.createIndex({ "workspace_id": 1 })
db.repositories.createIndex({ "github_repo_id": 1 }, { unique: true })
db.repositories.createIndex({ "full_name": 1 })
```

### Document Schema
```python
class Repository(Document):
    github_repo_id: int
    full_name: str
    name: str
    private: bool = False
    html_url: str
    default_branch: str = "main"
    workspace_id: PydanticObjectId
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    connected_by: PydanticObjectId

    class Settings:
        name = "repositories"
        use_state_management = True
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d2"),
  "github_repo_id": 987654321,
  "full_name": "myorg/myapp",
  "name": "myapp",
  "private": true,
  "html_url": "https://github.com/myorg/myapp",
  "default_branch": "main",
  "workspace_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
  "connected_at": ISODate("2026-09-01T10:00:00Z"),
  "connected_by": ObjectId("66f8a1b2c3d4e5f6a7b8c9d0")
}
```

---

## Collection: webhook_events

### Indexes
```javascript
db.webhook_events.createIndex({ "delivery_id": 1 }, { unique: true })
db.webhook_events.createIndex({ "installation_id": 1, "received_at": -1 })
db.webhook_events.createIndex({ "event_type": 1, "received_at": -1 })
db.webhook_events.createIndex({ "received_at": -1 }, { expireAfterSeconds: 2592000 })  // 30 days TTL
```

### Document Schema
```python
class WebhookEvent(Document):
    delivery_id: str
    event_type: str
    action: Optional[str] = None
    installation_id: Optional[int] = None
    repository_full_name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "webhook_events"
        use_state_management = True
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d3"),
  "delivery_id": "abc123-def456-ghi789",
  "event_type": "workflow_run",
  "action": "completed",
  "installation_id": 12345678,
  "repository_full_name": "myorg/myapp",
  "payload": {
    "action": "completed",
    "workflow_run": {
      "id": 12345,
      "name": "CI Pipeline",
      "head_branch": "feature/xyz",
      "head_sha": "abcdef1234567890",
      "conclusion": "failure",
      "html_url": "https://github.com/myorg/myapp/actions/runs/12345"
    },
    "repository": { "id": 987654321, "full_name": "myorg/myapp" },
    "installation": { "id": 12345678 }
  },
  "received_at": ISODate("2026-09-26T08:30:00Z")
}
```

---

## Collection: pipeline_runs

### Indexes
```javascript
db.pipeline_runs.createIndex({ "workspace_id": 1, "created_at": -1 })
db.pipeline_runs.createIndex({ "delivery_id": 1 }, { unique: true })
db.pipeline_runs.createIndex({ "run_id": 1 }, { sparse: true })
db.pipeline_runs.createIndex({ "health_status": 1 })
db.pipeline_runs.createIndex({ "monitor_status": 1 })
db.pipeline_runs.createIndex({ "diagnosis_status": 1 })
db.pipeline_runs.createIndex({ "risk_status": 1 })
db.pipeline_runs.createIndex({ "autofix_status": 1 })
db.pipeline_runs.createIndex({ "branch": 1 })
db.pipeline_runs.createIndex({ "commit_sha": 1 })
db.pipeline_runs.createIndex({ "created_at": -1 }, { expireAfterSeconds: 31536000 })  // 1 year TTL
```

### Document Schema
```python
class PipelineRun(Document):
    workspace_id: PydanticObjectId
    installation_id: Optional[int] = None
    repository_full_name: str
    delivery_id: str
    event_type: str
    action: Optional[str] = None
    run_id: Optional[int] = None
    workflow_status: Optional[str] = None
    workflow_name: Optional[str] = None
    workflow_url: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    triggered_by: Optional[str] = None
    conclusion: Optional[str] = None
    health_status: str = "unknown"              # unknown, healthy, failed
    kafka_status: str = "queued"                # queued, sent, failed, disabled
    monitor_status: str = "pending"             # pending, running, completed, failed
    diagnosis_status: str = "pending"           # pending, running, completed, failed
    risk_status: str = "pending"                # pending, running, completed, failed
    monitor_summary: Optional[str] = None
    monitor_report_json: Dict[str, Any] = Field(default_factory=dict)
    monitor_logs_excerpt: List[str] = Field(default_factory=list)
    diagnosis_report: Optional[str] = None
    diagnosis_report_json: Dict[str, Any] = Field(default_factory=dict)
    diagnosis_error: Optional[str] = None
    risk_score: Optional[int] = None            # 0-100
    risk_band: Optional[str] = None             # low, medium, high
    risk_report_json: Dict[str, Any] = Field(default_factory=dict)
    risk_inputs_json: Dict[str, Any] = Field(default_factory=dict)
    risk_error: Optional[str] = None
    risk_provider: Optional[str] = None
    risk_model: Optional[str] = None
    autofix_status: str = "pending"             # pending, running, completed, failed, not_applicable
    autofix_mode: Optional[str] = None          # report_only, auto_pr, approval_pr, auto_merge
    autofix_report_url: Optional[str] = None
    autofix_pr_url: Optional[str] = None
    autofix_execution_id: Optional[str] = None
    autofix_error: Optional[str] = None
    autofix_feedback_url: Optional[str] = None
    autofix_feedback_status: Optional[str] = None
    error_summary: Optional[str] = None
    diagnosis_provider: Optional[str] = None
    diagnosis_model: Optional[str] = None
    monitor_provider: Optional[str] = None
    monitor_model: Optional[str] = None
    raw_event: Dict[str, Any] = Field(default_factory=dict)
    enriched_event: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "pipeline_runs"
        use_state_management = True
```

### Status Enums
```python
# Health Status
HEALTH_STATUSES = ["unknown", "healthy", "failed"]

# Processing Statuses
PROCESSING_STATUSES = ["pending", "running", "completed", "failed"]

# Kafka Status
KAFKA_STATUSES = ["queued", "sent", "failed", "disabled"]

# Auto-fix Status
AUTOFIX_STATUSES = ["pending", "running", "completed", "failed", "not_applicable"]

# Auto-fix Mode
AUTOFIX_MODES = ["report_only", "auto_pr", "approval_pr", "auto_merge"]

# Risk Band
RISK_BANDS = ["low", "medium", "high"]
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d4"),
  "workspace_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
  "installation_id": 12345678,
  "repository_full_name": "myorg/myapp",
  "delivery_id": "abc123-def456-ghi789",
  "event_type": "workflow_run",
  "action": "completed",
  "run_id": 12345,
  "workflow_status": "completed",
  "workflow_name": "CI Pipeline",
  "workflow_url": "https://github.com/myorg/myapp/actions/runs/12345",
  "branch": "feature/xyz",
  "commit_sha": "abcdef1234567890",
  "triggered_by": "octocat",
  "conclusion": "failure",
  "health_status": "failed",
  "kafka_status": "sent",
  "monitor_status": "completed",
  "diagnosis_status": "completed",
  "risk_status": "completed",
  "monitor_summary": "Build failed with null pointer exception in user_service.py",
  "monitor_report_json": {
    "error_type": "NullPointerException",
    "error_keywords": ["null", "pointer", "exception"],
    "failed_step": "Run tests",
    "logs_excerpt": ["Error: null pointer at user_service.py:42"]
  },
  "monitor_logs_excerpt": ["Error: null pointer at user_service.py:42"],
  "diagnosis_report": "Null pointer in user_service.py when accessing user.profile...",
  "diagnosis_report_json": {
    "error_type": "NullPointerException",
    "possible_causes": [
      "User profile not loaded before access",
      "Race condition in profile loading"
    ],
    "latest_working_change": "Refactored user service (commit abc123)"
  },
  "diagnosis_error": null,
  "risk_score": 25,
  "risk_band": "low",
  "risk_report_json": {
    "risk_score": 25,
    "risk_band": "low",
    "signals": {
      "environment": "development",
      "diff_size": "small",
      "file_categories": ["business_logic"],
      "review_signals": ["has_reviewers"],
      "blast_radius": "single_service"
    },
    "plain_english_summary": "Low risk: Single file change in well-tested area"
  },
  "risk_inputs_json": {
    "branch": "feature/xyz",
    "diff_size": 42,
    "changed_files": ["src/user_service.py"],
    "has_reviewers": true,
    "is_hotfix": false
  },
  "risk_error": null,
  "risk_provider": "github_models",
  "risk_model": "gpt-4o-mini",
  "autofix_status": "completed",
  "autofix_mode": "approval_pr",
  "autofix_report_url": "https://app.pipelineiq.io/autofix/report?token=...",
  "autofix_pr_url": "https://github.com/myorg/myapp/pull/42",
  "autofix_execution_id": "66f8a1b2c3d4e5f6a7b8c9d5",
  "autofix_error": null,
  "autofix_feedback_url": "https://app.pipelineiq.io/autofix/feedback?token=...",
  "autofix_feedback_status": "requested",
  "error_summary": "Null pointer in user_service.py",
  "diagnosis_provider": "groq",
  "diagnosis_model": "openai/gpt-oss-120b",
  "monitor_provider": "github_models",
  "monitor_model": "openai/gpt-4o-mini",
  "raw_event": { ... },
  "enriched_event": { ... },
  "created_at": ISODate("2026-09-26T08:30:00Z"),
  "updated_at": ISODate("2026-09-26T08:45:00Z")
}
```

---

## Collection: autofix_executions

### Indexes
```javascript
db.autofix_executions.createIndex({ "workspace_id": 1, "created_at": -1 })
db.autofix_executions.createIndex({ "pipeline_run_id": 1 }, { unique: true })
db.autofix_executions.createIndex({ "signed_report_token": 1 }, { unique: true, sparse: true })
db.autofix_executions.createIndex({ "execution_status": 1 })
db.autofix_executions.createIndex({ "error_signature": 1 })
```

### Document Schema
```python
class AutoFixExecution(Document):
    workspace_id: PydanticObjectId
    pipeline_run_id: PydanticObjectId
    repository_full_name: str
    target_branch: str
    error_signature: str                      # Hash for deduplication
    risk_score: int
    policy_action: str                        # auto_fix, approval_required, block_only
    execution_status: str = "pending"         # pending, running, completed, failed
    reviewer_username: Optional[str] = None
    reviewer_github_id: Optional[int] = None
    mode: str = "report_only"                 # report_only, auto_pr, approval_pr, auto_merge
    proposed_fix_json: Dict[str, Any] = Field(default_factory=dict)
    report_json: Dict[str, Any] = Field(default_factory=dict)
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_state: Optional[str] = None            # open, closed, merged
    fix_branch: Optional[str] = None
    merge_sha: Optional[str] = None
    loop_blocked_reason: Optional[str] = None
    signed_report_token: Optional[str] = None
    report_feedback_status: Optional[str] = None
    report_feedback_note: Optional[str] = None
    resolution_feedback_status: Optional[str] = None
    resolution_feedback_url: Optional[str] = None
    resolution_feedback_requested_at: Optional[datetime] = None
    resolution_feedback_submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "autofix_executions"
        use_state_management = True
```

### Policy Action Values
```python
POLICY_ACTIONS = ["auto_fix", "approval_required", "block_only"]
```

### Execution Status Values
```python
EXECUTION_STATUSES = ["pending", "running", "completed", "failed"]
```

### Mode Values
```python
AUTOFIX_MODES = ["report_only", "auto_pr", "approval_pr", "auto_merge"]
```

### Report Feedback Status Values
```python
REPORT_FEEDBACK_STATUSES = [
    "requested", "approved_create_pr", "approved_and_merged",
    "approved_future_auto_merge", "rejected", "rejected_and_closed",
    "manual_only"
]
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d5"),
  "workspace_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
  "pipeline_run_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d4"),
  "repository_full_name": "myorg/myapp",
  "target_branch": "main",
  "error_signature": "sha256:abc123...",
  "risk_score": 25,
  "policy_action": "approval_required",
  "execution_status": "completed",
  "reviewer_username": "octocat",
  "reviewer_github_id": 583231,
  "mode": "approval_pr",
  "proposed_fix_json": {
    "summary": "Add null check in user_service.py",
    "files": [
      {
        "path": "src/user_service.py",
        "original_content": "def get_user_profile(user_id):\n    user = db.get(user_id)\n    return user.profile.name",
        "new_content": "def get_user_profile(user_id):\n    user = db.get(user_id)\n    if user and user.profile:\n        return user.profile.name\n    return None"
      }
    ]
  },
  "report_json": {
    "fix_summary": "Fix null pointer in user_service.py",
    "possible_fix_steps": [
      "Add null check before accessing user.profile",
      "Add unit test for null profile case"
    ],
    "risk": {
      "plain_english_summary": "Low risk: Single file change, well-tested area"
    },
    "branch": "pipelineiq/fix/abc123",
    "policy_note": "Risk score 25 is below auto-fix threshold but requires approval due to workspace policy"
  },
  "pr_number": 42,
  "pr_url": "https://github.com/myorg/myapp/pull/42",
  "pr_state": "open",
  "fix_branch": "pipelineiq/fix/abc123",
  "merge_sha": null,
  "loop_blocked_reason": null,
  "signed_report_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "report_feedback_status": "approved_create_pr",
  "report_feedback_note": "Looks good, please merge",
  "resolution_feedback_status": "requested",
  "resolution_feedback_url": "https://app.pipelineiq.io/autofix/feedback?token=...",
  "resolution_feedback_requested_at": ISODate("2026-09-26T10:00:00Z"),
  "resolution_feedback_submitted_at": null,
  "created_at": ISODate("2026-09-26T08:35:00Z"),
  "updated_at": ISODate("2026-09-26T09:00:00Z")
}
```

---

## Collection: autofix_feedbacks

### Indexes
```javascript
db.autofix_feedbacks.createIndex({ "workspace_id": 1, "created_at": -1 })
db.autofix_feedbacks.createIndex({ "execution_id": 1 }, { unique: true })
db.autofix_feedbacks.createIndex({ "feedback_token": 1 }, { unique: true })
db.autofix_feedbacks.createIndex({ "status": 1 })
db.autofix_feedbacks.createIndex({ "error_signature": 1 })
```

### Document Schema
```python
class AutoFixFeedback(Document):
    workspace_id: PydanticObjectId
    execution_id: PydanticObjectId
    pipeline_run_id: PydanticObjectId
    repository_full_name: str
    error_signature: str
    target_branch: str
    reviewer_username: Optional[str] = None
    reviewer_github_id: Optional[int] = None
    feedback_token: str
    feedback_url: str
    status: str = "requested"                 # requested, submitted
    outcome: Optional[str] = None             # resolved, partially_resolved, not_resolved
    automation_quality: Optional[str] = None  # excellent, acceptable, poor
    should_auto_apply_similar: Optional[bool] = None
    notes: Optional[str] = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "autofix_feedbacks"
        use_state_management = True
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d6"),
  "workspace_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
  "execution_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d5"),
  "pipeline_run_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d4"),
  "repository_full_name": "myorg/myapp",
  "error_signature": "sha256:abc123...",
  "target_branch": "main",
  "reviewer_username": "octocat",
  "reviewer_github_id": 583231,
  "feedback_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "feedback_url": "https://app.pipelineiq.io/autofix/feedback?token=...",
  "status": "submitted",
  "outcome": "resolved",
  "automation_quality": "excellent",
  "should_auto_apply_similar": true,
  "notes": "Fix was perfect, saved hours of debugging",
  "requested_at": ISODate("2026-09-26T10:00:00Z"),
  "submitted_at": ISODate("2026-09-26T14:30:00Z"),
  "created_at": ISODate("2026-09-26T10:00:00Z"),
  "updated_at": ISODate("2026-09-26T14:30:00Z")
}
```

---

## Collection: autofix_memories

### Indexes
```javascript
db.autofix_memories.createIndex({ "workspace_id": 1, "error_signature": 1 }, { unique: true })
db.autofix_memories.createIndex({ "repository_full_name": 1, "error_signature": 1 })
db.autofix_memories.createIndex({ "approved_for_auto_merge": 1 })
```

### Document Schema
```python
class AutoFixMemory(Document):
    workspace_id: PydanticObjectId
    repository_full_name: str
    error_signature: str
    memory_type: str                          # "report_feedback", "resolution_feedback"
    reviewer_username: Optional[str] = None
    reviewer_github_id: Optional[int] = None
    note: Optional[str] = None
    approved_for_auto_merge: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "autofix_memories"
        use_state_management = True
```

### Example Document
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d7"),
  "workspace_id": ObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
  "repository_full_name": "myorg/myapp",
  "error_signature": "sha256:abc123...",
  "memory_type": "resolution_feedback",
  "reviewer_username": "octocat",
  "reviewer_github_id": 583231,
  "note": "Fix was perfect, saved hours of debugging",
  "approved_for_auto_merge": true,
  "created_at": ISODate("2026-09-26T14:30:00Z"),
  "updated_at": ISODate("2026-09-26T14:30:00Z")
}
```

---

## Relationships Diagram

```
User (1) ─────< (N) Workspace
Workspace (1) ─────< (N) Repository
Workspace (1) ─────< (N) PipelineRun
Workspace (1) ─────< (N) AutoFixExecution
Workspace (1) ─────< (N) AutoFixFeedback
Workspace (1) ─────< (N) AutoFixMemory

PipelineRun (1) ───── (1) AutoFixExecution
AutoFixExecution (1) ───── (1) AutoFixFeedback

WebhookEvent (N) ───── (1) Workspace (via installation_id)
```

---

## Migration Notes

### From Original Schema
1. **User**: Added `organizations` array, `is_active` flag
2. **Workspace**: Added `slack_devops_mention`, `risk_profile` embedded, `last_webhook_event_at`
3. **PipelineRun**: Added comprehensive status tracking, LLM provider/model fields, `raw_event`/`enriched_event`
4. **AutoFixExecution**: Added `mode`, `report_feedback_*`, `resolution_feedback_*`, `loop_blocked_reason`
5. **AutoFixFeedback**: New collection for resolution feedback
6. **AutoFixMemory**: New collection for learned patterns
7. **Repository**: New collection for multi-repo support (future)

### Field-Level Encryption
Sensitive fields that should be encrypted at rest:
- `User.github_access_token`
- `Workspace.github_installation_id` (consider)
- `AutoFixExecution.signed_report_token`
- `AutoFixFeedback.feedback_token`

---

## Query Patterns

### Common Queries

```python
# Get user's workspaces
workspaces = await Workspace.find(Workspace.owner_id == user.id).to_list()

# Get pipeline runs for workspace (paginated)
runs = await PipelineRun.find(PipelineRun.workspace_id == workspace.id)\
    .sort(-PipelineRun.created_at)\
    .skip(skip).limit(limit)\
    .to_list()

# Get failed runs needing diagnosis
failed_runs = await PipelineRun.find(
    PipelineRun.workspace_id == workspace.id,
    PipelineRun.health_status == "failed",
    PipelineRun.diagnosis_status == "pending"
).to_list()

# Get auto-fix executions by status
executions = await AutoFixExecution.find(
    AutoFixExecution.workspace_id == workspace.id,
    AutoFixExecution.execution_status.in_(["pending", "running"])
).to_list()

# Check memory for error signature
memory = await AutoFixMemory.find_one(
    AutoFixMemory.workspace_id == workspace.id,
    AutoFixMemory.error_signature == error_sig
)
```

---

*This document is the source of truth for data models. Update models in code first, then regenerate this document.*
