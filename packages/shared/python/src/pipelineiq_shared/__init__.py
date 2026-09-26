"""Framework-independent Python contracts shared by PipelineIQ services."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class HealthStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    FAILED = "failed"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskProfile(BaseModel):
    production_branch: str = Field(default="main", min_length=1, max_length=50)
    require_approval_above: int = Field(default=60, ge=0, le=100)
    auto_fix_below: int = Field(default=30, ge=0, le=100)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "RiskProfile":
        if self.auto_fix_below > self.require_approval_above:
            raise ValueError("auto_fix_below must be <= require_approval_above")
        return self


__all__ = ["HealthStatus", "ProcessingStatus", "RiskProfile"]

