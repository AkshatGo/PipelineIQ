"""Tests for AI Safety Service."""

import pytest
import fnmatch
from beanie import PydanticObjectId

from pipelineiq.services.ai_safety import (
    AISafetyService,
    AgentConfig,
    AIConstraint,
    SafetyCheckResult,
    AIPermissionLevel,
    AICapability,
    ConstraintType,
)


@pytest.fixture
def ai_safety_service():
    return AISafetyService()


class TestAISafetyService:
    """Tests for AISafetyService class."""

    def test_default_agents_exist(self, ai_safety_service):
        """Test that default agents are configured."""
        assert "monitor" in ai_safety_service.DEFAULT_AGENTS
        assert "diagnosis" in ai_safety_service.DEFAULT_AGENTS
        assert "risk" in ai_safety_service.DEFAULT_AGENTS
        assert "autofix" in ai_safety_service.DEFAULT_AGENTS

    def test_monitor_agent_config(self, ai_safety_service):
        """Test monitor agent configuration."""
        config = ai_safety_service.get_agent_config("monitor")
        assert config is not None
        assert config.agent_type == "monitor"
        assert config.name == "Log Analyzer"
        assert config.permission == AIPermissionLevel.SUGGESTION_ONLY
        assert AICapability.ANALYZE_LOGS in config.capabilities
        assert AICapability.FETCH_DIFF in config.capabilities
        assert len(config.constraints) == 0

    def test_diagnosis_agent_config(self, ai_safety_service):
        """Test diagnosis agent configuration."""
        config = ai_safety_service.get_agent_config("diagnosis")
        assert config is not None
        assert config.agent_type == "diagnosis"
        assert config.name == "Root Cause Analyzer"
        assert config.permission == AIPermissionLevel.SUGGESTION_ONLY
        assert AICapability.GENERATE_DIAGNOSIS in config.capabilities

    def test_risk_agent_config(self, ai_safety_service):
        """Test risk agent configuration."""
        config = ai_safety_service.get_agent_config("risk")
        assert config is not None
        assert config.agent_type == "risk"
        assert config.name == "Risk Assessor"
        assert config.permission == AIPermissionLevel.SUGGESTION_ONLY
        assert AICapability.ANALYZE_LOGS in config.capabilities

    def test_autofix_agent_config(self, ai_safety_service):
        """Test autofix agent configuration with constraints."""
        config = ai_safety_service.get_agent_config("autofix")
        assert config is not None
        assert config.agent_type == "autofix"
        assert config.name == "Code Fixer"
        assert config.permission == AIPermissionLevel.APPLY_WITH_APPROVAL
        assert AICapability.GENERATE_FIX in config.capabilities
        assert AICapability.CREATE_PR in config.capabilities
        assert AICapability.READ_FILE in config.capabilities
        assert AICapability.WRITE_FILE in config.capabilities
        assert len(config.constraints) > 0

    def test_unknown_agent_returns_none(self, ai_safety_service):
        """Test that unknown agent returns None."""
        config = ai_safety_service.get_agent_config("unknown")
        assert config is None

    def test_check_safety_suggestion_only_blocks_write(self, ai_safety_service):
        """Test that suggestion-only agents cannot write files."""
        result = ai_safety_service.check_safety(
            agent_type="monitor",
            operation=AICapability.WRITE_FILE,
        )

        assert result.allowed is False
        assert result.requires_approval is True
        assert "suggestion-only" in result.reason.lower()

    def test_check_safety_missing_capability(self, ai_safety_service):
        """Test check_safety when agent lacks capability."""
        result = ai_safety_service.check_safety(
            agent_type="monitor",
            operation=AICapability.CREATE_PR,
        )

        assert result.allowed is False
        # The check first checks permission level (suggestion-only blocks CREATE_PR)
        # before checking capabilities, so reason mentions suggestion-only
        assert "suggestion-only" in result.reason or "lacks capability" in result.reason

    def test_check_safety_file_pattern_constraint(self, ai_safety_service):
        """Test file pattern constraint matching."""
        result = ai_safety_service.check_safety(
            agent_type="autofix",
            operation=AICapability.WRITE_FILE,
            file_path="main.tf",
        )

        assert result.allowed is False or result.requires_approval is True
        assert len(result.matched_constraints) > 0
        assert any(c.type == ConstraintType.FILE_PATTERN for c in result.matched_constraints)

    def test_check_safety_docker_compose_constraint(self, ai_safety_service):
        """Test docker-compose file constraint."""
        result = ai_safety_service.check_safety(
            agent_type="autofix",
            operation=AICapability.WRITE_FILE,
            file_path="docker-compose.yml",
        )

        assert result.allowed is False or result.requires_approval is True
        assert any(c.pattern and "docker-compose" in c.pattern for c in result.matched_constraints)

    def test_check_safety_migrations_constraint(self, ai_safety_service):
        """Test migrations folder constraint."""
        result = ai_safety_service.check_safety(
            agent_type="autofix",
            operation=AICapability.WRITE_FILE,
            file_path="src/migrations/001_create_users.sql",
        )

        assert result.allowed is False or result.requires_approval is True
        assert any(c.pattern and "migrations" in c.pattern for c in result.matched_constraints)

    def test_check_safety_branch_protection(self, ai_safety_service):
        """Test branch protection constraint."""
        result = ai_safety_service.check_safety(
            agent_type="autofix",
            operation=AICapability.WRITE_FILE,
            file_path="src/main.py",
            branch="main",
        )

        assert result.allowed is False or result.requires_approval is True
        assert any(c.type == ConstraintType.BRANCH for c in result.matched_constraints)

    def test_check_safety_branch_protection_release(self, ai_safety_service):
        """Test branch protection for release branches."""
        result = ai_safety_service.check_safety(
            agent_type="autofix",
            operation=AICapability.WRITE_FILE,
            file_path="src/main.py",
            branch="release/v1.0",
        )

        assert result.allowed is False or result.requires_approval is True
        matched = [c for c in ai_safety_service.get_agent_config("autofix").constraints
                   if c.type == ConstraintType.BRANCH]
        assert any(fnmatch.fnmatch("release/v1.0", pattern) for pattern in matched[0].branches)

    def test_check_safety_delete_file_requires_approval(self, ai_safety_service):
        """Test that delete file operation requires approval."""
        result = ai_safety_service.check_safety(
            agent_type="autofix",
            operation=AICapability.DELETE_FILE,
        )

        assert result.allowed is False or result.requires_approval is True

    def test_check_safety_safe_change_auto_apply(self, ai_safety_service):
        """Test safe change classification for auto-apply."""
        from pipelineiq.services.ai_safety import AgentConfig, AIConstraint, AICapability, ConstraintType

        safe_config = AgentConfig(
            agent_type="test_safe",
            name="Safe Agent",
            permission=AIPermissionLevel.AUTO_APPLY_SAFE,
            capabilities=[AICapability.WRITE_FILE],
            constraints=[],
        )

        # Patch the instance's DEFAULT_AGENTS temporarily
        original_agents = ai_safety_service.DEFAULT_AGENTS.copy()
        ai_safety_service.DEFAULT_AGENTS = {"test_safe": safe_config}

        try:
            result = ai_safety_service.check_safety(
                agent_type="test_safe",
                operation=AICapability.WRITE_FILE,
                file_path="README.md",
            )

            assert result.allowed is True
            assert result.safe_change is True
        finally:
            ai_safety_service.DEFAULT_AGENTS = original_agents

    def test_check_safety_unsafe_file_not_auto_applied(self, ai_safety_service):
        """Test that unsafe files are not auto-applied."""
        from pipelineiq.services.ai_safety import AgentConfig, AICapability, AIPermissionLevel

        safe_config = AgentConfig(
            agent_type="test_safe",
            name="Safe Agent",
            permission=AIPermissionLevel.AUTO_APPLY_SAFE,
            capabilities=[AICapability.WRITE_FILE],
            constraints=[],
        )

        # Modify the service instance's DEFAULT_AGENTS
        original_agents = ai_safety_service.DEFAULT_AGENTS.copy()
        ai_safety_service.DEFAULT_AGENTS = {"test_safe": safe_config}

        try:
            result = ai_safety_service.check_safety(
                agent_type="test_safe",
                operation=AICapability.WRITE_FILE,
                file_path="main.tf",  # Unsafe pattern
            )

            assert result.safe_change is False
        finally:
            ai_safety_service.DEFAULT_AGENTS = original_agents

    def test_check_safety_unknown_agent(self, ai_safety_service):
        """Test check_safety with unknown agent type."""
        result = ai_safety_service.check_safety(
            agent_type="unknown",
            operation=AICapability.READ_FILE,
        )

        assert result.allowed is False
        assert "Unknown agent type" in result.reason

    def test_register_agent(self, ai_safety_service):
        """Test registering a custom agent."""
        from pipelineiq.services.ai_safety import AgentConfig, AICapability

        custom_config = AgentConfig(
            agent_type="custom",
            name="Custom Agent",
            capabilities=[AICapability.READ_FILE],
        )

        ai_safety_service.register_agent("custom", custom_config)
        config = ai_safety_service.get_agent_config("custom")

        assert config is not None
        assert config.agent_type == "custom"
        assert config.name == "Custom Agent"

    def test_safe_change_classification(self, ai_safety_service):
        """Test safe change classification logic."""
        from pipelineiq.services.ai_safety import AgentConfig, AICapability, AIPermissionLevel

        # Create a test agent with AUTO_APPLY_SAFE permission for testing
        safe_config = AgentConfig(
            agent_type="test_safe",
            name="Safe Agent",
            permission=AIPermissionLevel.AUTO_APPLY_SAFE,
            capabilities=[AICapability.WRITE_FILE],
            constraints=[],
        )
        original_agents = ai_safety_service.DEFAULT_AGENTS.copy()
        ai_safety_service.DEFAULT_AGENTS["test_safe"] = safe_config

        try:
            # Test unsafe patterns
            unsafe_files = [
                "main.tf",
                "docker-compose.yml",
                "src/migrations/001.sql",
                "script.sh",
                ".github/workflows/ci.yml",
                "schema.sql",
            ]

            for file_path in unsafe_files:
                is_safe = ai_safety_service._is_safe_change(
                    ai_safety_service.get_agent_config("test_safe"),
                    AICapability.WRITE_FILE,
                    file_path,
                    None,
                )
                assert is_safe is False, f"Expected {file_path} to be unsafe"

            # Test safe patterns
            safe_files = [
                "README.md",
                "docs/guide.txt",
                "config.json",
                "config.yaml",
                "tests/test_main.py",
                "test_main.py",
            ]

            for file_path in safe_files:
                is_safe = ai_safety_service._is_safe_change(
                    ai_safety_service.get_agent_config("test_safe"),
                    AICapability.WRITE_FILE,
                    file_path,
                    None,
                )
                assert is_safe is True, f"Expected {file_path} to be safe"
        finally:
            # Restore original agents
            ai_safety_service.DEFAULT_AGENTS = {
                k: v for k, v in ai_safety_service.DEFAULT_AGENTS.items() if k != "test_safe"
            }

    def test_ai_constraint_model(self):
        """Test AIConstraint model."""
        constraint = AIConstraint(
            type=ConstraintType.FILE_PATTERN,
            pattern=r".*\.tf$",
            operations=[AICapability.WRITE_FILE],
            branches=["main"],
            reason="Terraform files need review",
            severity="error",
        )

        assert constraint.type == ConstraintType.FILE_PATTERN
        assert constraint.pattern == r".*\.tf$"
        assert constraint.reason == "Terraform files need review"

    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        from pipelineiq.services.ai_safety import AgentConfig

        config = AgentConfig(agent_type="test", name="Test")
        assert config.permission == AIPermissionLevel.SUGGESTION_ONLY
        assert config.capabilities == []
        assert config.constraints == []
        assert config.max_tokens == 8000
        assert config.temperature == 0.1

    def test_safety_check_result_defaults(self):
        """Test SafetyCheckResult default values."""
        from pipelineiq.services.ai_safety import SafetyCheckResult

        result = SafetyCheckResult(allowed=True)
        assert result.allowed is True
        assert result.reason is None
        assert result.requires_approval is False
        assert result.matched_constraints == []
        assert result.safe_change is False