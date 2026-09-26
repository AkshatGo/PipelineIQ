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

