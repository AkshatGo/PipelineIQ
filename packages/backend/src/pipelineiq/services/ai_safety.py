"""AI Safety & Control Service: Permission gates and constraint system for AI agents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field


class AIPermissionLevel(str, Enum):
    """Permission levels for AI agents."""

    SUGGESTION_ONLY = "suggestion_only"
    APPLY_WITH_APPROVAL = "apply_with_approval"
    AUTO_APPLY_SAFE = "auto_apply_safe"
    RESTRICTED_AUTOMATION = "restricted_automation"


class AICapability(str, Enum):
    """Capabilities that AI agents can have."""

    ANALYZE_LOGS = "analyze_logs"
    FETCH_DIFF = "fetch_diff"
    GENERATE_DIAGNOSIS = "generate_diagnosis"
    GENERATE_FIX = "generate_fix"
    CREATE_PR = "create_pr"
    REQUEST_REVIEW = "request_review"
    MERGE_PR = "merge_pr"
    RUN_TESTS = "run_tests"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"


class ConstraintType(str, Enum):
    """Types of safety constraints."""

    FILE_PATTERN = "file_pattern"
    OPERATION = "operation"
    BRANCH = "branch"
    REQUIRES_APPROVAL = "requires_approval"
    SAFE_CHANGE = "safe_change"


class AIConstraint(BaseModel):
    """Safety constraint for AI agents."""

    type: ConstraintType
    pattern: str | None = None
    operations: list[AICapability] | None = None
    branches: list[str] | None = None
    reason: str
    severity: str = "error"


class AgentConfig(BaseModel):
    """Configuration for an AI agent with safety controls."""

    agent_type: str
    name: str
    permission: AIPermissionLevel = AIPermissionLevel.SUGGESTION_ONLY
    capabilities: list[AICapability] = Field(default_factory=list)
    constraints: list[AIConstraint] = Field(default_factory=list)
    fallback_provider: str | None = None
    max_tokens: int = 8000
    temperature: float = 0.1


class SafetyCheckResult(BaseModel):
    """Result of a safety check."""

    allowed: bool
    reason: str | None = None
    requires_approval: bool = False
    matched_constraints: list[AIConstraint] = Field(default_factory=list)
    safe_change: bool = False


class SafetyCheckRequest(BaseModel):
    agent_type: str
    operation: AICapability
    file_path: str | None = None
    branch: str | None = None


@dataclass
class AISafetyService:
    """Service for enforcing AI safety constraints."""

    DEFAULT_AGENTS: dict[str, AgentConfig] = field(
        default_factory=lambda: {
            "monitor": AgentConfig(
                agent_type="monitor",
                name="Log Analyzer",
                permission="AIPermissionLevel.SUGGESTION_ONLY",
                capabilities=[
                    "AICapability.ANALYZE_LOGS",
                    "AICapability.FETCH_DIFF",
                ],
                constraints=[],
            ),
            "diagnosis": AgentConfig(
                agent_type="diagnosis",
                name="Root Cause Analyzer",
                permission="AIPermissionLevel.SUGGESTION_ONLY",
                capabilities=["AICapability.GENERATE_DIAGNOSIS"],
                constraints=[],
            ),
            "risk": AgentConfig(
                agent_type="risk",
                name="Risk Assessor",
                permission="AIPermissionLevel.SUGGESTION_ONLY",
                capabilities=["AICapability.ANALYZE_LOGS"],
                constraints=[],
            ),
            "autofix": AgentConfig(
                agent_type="autofix",
                name="Code Fixer",
                permission="AIPermissionLevel.APPLY_WITH_APPROVAL",
                capabilities=[
                    "AICapability.GENERATE_FIX",
                    "AICapability.CREATE_PR",
                    "AICapability.READ_FILE",
                    "AICapability.WRITE_FILE",
                ],
                constraints=[
                    AIConstraint(
                        type="ConstraintType.FILE_PATTERN",
                        pattern=r".*\.tf$",
                        reason="Infrastructure changes require approval",
                    ),
                    AIConstraint(
                        type="ConstraintType.FILE_PATTERN",
                        pattern=r"docker-compose.*\.ya?ml$",
                        reason="Container config changes need review",
                    ),
                    AIConstraint(
                        type="ConstraintType.FILE_PATTERN",
                        pattern=r".*/migrations/.*",
                        reason="Database migrations require manual review",
                    ),
                    AIConstraint(
                        type="ConstraintType.BRANCH",
                        branches=["main", "production", "release/*"],
                        reason="Protected branches require approval",
                    ),
                    AIConstraint(
                        type="ConstraintType.OPERATION",
                        operations=[
                            "AICapability.DELETE_FILE",
                        ],
                        reason="Destructive operations need approval",
                    ),
                    AIConstraint(
                        type="ConstraintType.FILE_PATTERN",
                        pattern=r".*\.sql$",
                        reason="SQL files require review",
                    ),
                    AIConstraint(
                        type="ConstraintType.FILE_PATTERN",
                        pattern=r".*\.sh$",
                        reason="Shell scripts require review",
                    ),
                    AIConstraint(
                        type="ConstraintType.FILE_PATTERN",
                        pattern=r"\.github/workflows/.*",
                        reason="CI/CD workflow changes need review",
                    ),
                ],
            ),
        }
    )

    def get_agent_config(self, agent_type: str) -> AgentConfig | None:
        """Get configuration for an agent type."""
        return self.DEFAULT_AGENTS.get(agent_type)

    def check_safety(
        self,
        agent_type: str,
        operation: AICapability,
        file_path: str | None = None,
        branch: str | None = None,
    ) -> SafetyCheckResult:
        """Check if an AI operation is allowed under safety constraints."""
        config = self.get_agent_config(agent_type)
        if not config:
            return SafetyCheckResult(
                allowed=False,
                reason=f"Unknown agent type: {agent_type}",
            )

        # Check permission level
        if config.permission == "AIPermissionLevel.SUGGESTION_ONLY":
            if operation in {
                "AICapability.WRITE_FILE",
                "AICapability.DELETE_FILE",
                "AICapability.CREATE_PR",
                "AICapability.MERGE_PR",
            }:
                return SafetyCheckResult(
                    allowed=False,
                    reason=f"Agent {agent_type} is suggestion-only. Cannot {operation.value}.",
                    requires_approval=True,
                )

        # Check capabilities
        if operation not in config.capabilities:
            return SafetyCheckResult(
                allowed=False,
                reason=f"Agent {agent_type} lacks capability: {operation.value}",
            )

        # Check constraints
        matched_constraints: list[AIConstraint] = []
        for constraint in config.constraints:
            if constraint.type == "ConstraintType.FILE_PATTERN" and file_path:
                if constraint.pattern and re.match(constraint.pattern, file_path):
                    matched_constraints.append(constraint)
            elif constraint.type == "ConstraintType.OPERATION" and operation in (
                constraint.operations or []
            ):
                matched_constraints.append(constraint)
            elif constraint.type == "ConstraintType.BRANCH" and branch:
                for branch_pattern in constraint.branches or []:
                    import fnmatch

                    if fnmatch.fnmatch(branch, branch_pattern):
                        matched_constraints.append(constraint)
                        break

        if matched_constraints:
            requires_approval = any(
                c.type == "ConstraintType.REQUIRES_APPROVAL" for c in matched_constraints
            )
            if requires_approval or config.permission == "AIPermissionLevel.APPLY_WITH_APPROVAL":
                return SafetyCheckResult(
                    allowed=True,
                    reason="Operation requires human approval",
                    requires_approval=True,
                    matched_constraints=matched_constraints,
                )
            return SafetyCheckResult(
                allowed=False,
                reason="Operation blocked by constraints: "
                f"{[c.reason for c in matched_constraints]}",
                matched_constraints=matched_constraints,
            )

        safe_change = self._is_safe_change(config, operation, file_path, branch)

        if config.permission == "AIPermissionLevel.AUTO_APPLY_SAFE" and safe_change:
            return SafetyCheckResult(
                allowed=True,
                reason="Safe change - auto-apply allowed",
                safe_change=True,
            )

        return SafetyCheckResult(
            allowed=True,
            reason="Operation allowed",
            safe_change=safe_change,
        )

    def _is_safe_change(
        self,
        config: AgentConfig,
        operation: AICapability,
        file_path: str | None,
        branch: str | None,
    ) -> bool:
        """Determine if a change is safe for auto-apply."""
        if config.permission != "AIPermissionLevel.AUTO_APPLY_SAFE":
            return False

        if not file_path:
            return False

        unsafe_patterns = [
            r".*\.tf$",
            r"docker-compose.*",
            r".*/migrations/.*",
            r".*\.sql$",
            r".*\.sh$",
            r"\.github/workflows/.*",
        ]

        for pattern in unsafe_patterns:
            if re.match(pattern, file_path):
                return False

        safe_patterns = [
            r".*\.md$",
            r".*\.txt$",
            r".*\.json$",
            r".*\.yaml$",
            r".*\.yml$",
            r"tests/.*",
            r".*_test\..*",
        ]

        return any(re.match(pattern, file_path) for pattern in safe_patterns)

    def register_agent(self, agent_type: str, config: AgentConfig) -> None:
        """Register a custom agent configuration."""
        self.DEFAULT_AGENTS[agent_type] = config


_ai_safety_service: AISafetyService | None = None


def get_ai_safety_service() -> AISafetyService:
    """Get or create the global AI safety service instance."""
    global _ai_safety_service
    if _ai_safety_service is None:
        _ai_safety_service = AISafetyService()
    return _ai_safety_service