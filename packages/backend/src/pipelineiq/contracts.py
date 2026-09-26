from enum import StrEnum

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
