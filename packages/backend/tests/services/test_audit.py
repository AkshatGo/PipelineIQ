"""Tests for AuditService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime
from beanie import PydanticObjectId

from pipelineiq.services.audit import AuditService
from pipelineiq.models import IncidentEvent


@pytest.fixture
def audit_service():
    return AuditService()


@pytest.fixture
def sample_incident_id():
    return PydanticObjectId()


@pytest.fixture
def sample_workspace_id():
    return PydanticObjectId()


@pytest.fixture
def sample_user_id():
    return PydanticObjectId()


class TestAuditService:
    """Tests for AuditService class."""

    @pytest.mark.asyncio
    async def test_log_event_basic(self, audit_service, sample_incident_id, sample_workspace_id, sample_user_id):
        """Test basic event logging."""
        mock_event = MagicMock()
        mock_event.incident_id = sample_incident_id
        mock_event.workspace_id = sample_workspace_id
        mock_event.actor_type = "human"
        mock_event.type = "workspace.document_edited"
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await audit_service.log_event(
                incident_id=sample_incident_id,
                workspace_id=sample_workspace_id,
                actor_id=PydanticObjectId(),
                actor_type="human",
                actor_name="test_user",
                event_type="workspace.document_edited",
                action="edit",
                description="Modified file: test.py",
            )

            assert event.incident_id == sample_incident_id
            assert event.workspace_id == sample_workspace_id
            assert event.actor_type == "human"
            assert event.type == "workspace.document_edited"

    @pytest.mark.asyncio
    async def test_log_event_invalid_actor_type(self, audit_service, sample_incident_id, sample_workspace_id):
        """Test event logging with invalid actor type."""
        with pytest.raises(ValueError, match="Invalid actor_type"):
            await audit_service.log_event(
                incident_id=sample_incident_id,
                workspace_id=sample_workspace_id,
                actor_id=PydanticObjectId(),
                actor_type="invalid",
                actor_name="test_user",
                event_type="test.event",
                action="test",
                description="test",
            )

    @pytest.mark.asyncio
    async def test_log_incident_created(self, audit_service, sample_incident_id):
        """Test logging incident creation."""
        mock_event = MagicMock()
        mock_event.type = "incident.created"
        mock_event.action = "create"
        mock_event.actor_type = "system"
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await audit_service.log_incident_created(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_name="test_user",
            )

            assert event.type == "incident.created"
            assert event.action == "create"
            assert event.actor_type == "system"

    @pytest.mark.asyncio
    async def test_log_document_edited(self, audit_service):
        """Test logging document edit."""
        mock_event = MagicMock()
        mock_event.type = "workspace.document_edited"
        mock_event.action = "edit"
        mock_event.document_id = PydanticObjectId()
        mock_event.metadata = {"path": "test.py"}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await audit_service.log_document_edited(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_type="human",
                actor_name="test_user",
                document_id=PydanticObjectId(),
                path="test.py",
                before_content="old content",
                after_content="new content",
            )

            assert event.type == "workspace.document_edited"
            assert event.action == "edit"
            assert event.document_id is not None
            assert event.metadata["path"] == "test.py"

    @pytest.mark.asyncio
    async def test_log_checkpoint_created(self, audit_service):
        """Test logging checkpoint creation."""
        mock_event = MagicMock()
        mock_event.type = "version.checkpoint_created"
        mock_event.action = "checkpoint"
        mock_event.version_id = PydanticObjectId()
        mock_event.metadata = {"tags": ["bugfix", "urgent"]}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await audit_service.log_checkpoint_created(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_type="human",
                actor_name="test_user",
                document_id=PydanticObjectId(),
                version_id=PydanticObjectId(),
                message="Fixed bug",
                tags=["bugfix", "urgent"],
            )

            assert event.type == "version.checkpoint_created"
            assert event.action == "checkpoint"
            assert event.version_id is not None
            assert event.metadata["tags"] == ["bugfix", "urgent"]

    @pytest.mark.asyncio
    async def test_log_version_restored(self, audit_service):
        """Test logging version restoration."""
        mock_event = MagicMock()
        mock_event.type = "version.restored"
        mock_event.action = "restore"
        mock_event.metadata = {"restored_from_version": 5}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await audit_service.log_version_restored(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_type="human",
                actor_name="test_user",
                document_id=PydanticObjectId(),
                version_id=PydanticObjectId(),
                restored_from_version=5,
            )

            assert event.type == "version.restored"
            assert event.action == "restore"
            assert event.metadata["restored_from_version"] == 5

    @pytest.mark.asyncio
    async def test_log_ai_suggestion(self, audit_service):
        """Test logging AI suggestion."""
        mock_event = MagicMock()
        mock_event.actor_type = "ai"
        mock_event.type = "ai.fix_proposed"
        mock_event.action = "suggest"
        mock_event.metadata = {"confidence": 0.95, "agent_type": "autofix", "file": "test.py"}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_ai_suggestion(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                agent_type="autofix",
                suggestion_type="fix",
                description="Fix null pointer",
                confidence=0.95,
                metadata={"file": "test.py"},
            )

            assert event.actor_type == "ai"
            assert event.type == "ai.fix_proposed"
            assert event.action == "suggest"
            assert event.metadata["confidence"] == 0.95
            assert event.metadata["agent_type"] == "autofix"
            assert event.metadata["file"] == "test.py"

    @pytest.mark.asyncio
    async def test_log_ai_suggestion_outcome(self, audit_service):
        """Test logging AI suggestion outcome."""
        mock_event = MagicMock()
        mock_event.type = "ai.suggestion_accepted"
        mock_event.action = "accepted"
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_ai_suggestion_outcome(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_type="human",
                actor_name="test_user",
                suggestion_type="fix",
                outcome="accepted",
                document_id=PydanticObjectId(),
            )

            assert event.type == "ai.suggestion_accepted"
            assert event.action == "accepted"

    @pytest.mark.asyncio
    async def test_log_human_action(self, audit_service):
        """Test logging human action."""
        mock_event = MagicMock()
        mock_event.actor_type = "human"
        mock_event.type = "human.approved_changes"
        mock_event.action = "approved_changes"
        mock_event.metadata = {"pr_number": 42}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_human_action(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_name="test_user",
                action="approved_changes",
                description="Approved the fix",
                document_id=PydanticObjectId(),
                metadata={"pr_number": 42},
            )

            assert event.actor_type == "human"
            assert event.type == "human.approved_changes"
            assert event.action == "approved_changes"
            assert event.metadata["pr_number"] == 42

    @pytest.mark.asyncio
    async def test_log_validation_started(self, audit_service):
        """Test logging validation start."""
        mock_event = MagicMock()
        mock_event.type = "ci.validation_started"
        mock_event.action = "start"
        mock_event.metadata = {"validation_run_id": str(PydanticObjectId())}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_validation_started(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                validation_run_id=PydanticObjectId(),
                triggered_by=PydanticObjectId(),
            )

            assert event.type == "ci.validation_started"
            assert event.action == "start"
            assert event.metadata["validation_run_id"] is not None

    @pytest.mark.asyncio
    async def test_log_validation_completed_passed(self, audit_service):
        """Test logging validation completion (passed)."""
        mock_event = MagicMock()
        mock_event.type = "ci.validation_passed"
        mock_event.action = "complete"
        mock_event.metadata = {"validation_run_id": str(PydanticObjectId()), "stages": [{"name": "lint", "status": "passed"}]}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_validation_completed(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                validation_run_id=PydanticObjectId(),
                status="passed",
                stage_results=[{"name": "lint", "status": "passed"}],
            )

            assert event.type == "ci.validation_passed"
            assert event.action == "complete"
            assert event.metadata["validation_run_id"] is not None
            assert event.metadata["stages"][0]["status"] == "passed"

    @pytest.mark.asyncio
    async def test_log_validation_completed_failed(self, audit_service):
        """Test logging validation completion (failed)."""
        mock_event = MagicMock()
        mock_event.type = "ci.validation_failed"
        mock_event.metadata = {"stages": [{"name": "lint", "status": "failed", "error": "lint error"}]}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_validation_completed(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                validation_run_id=PydanticObjectId(),
                status="failed",
                stage_results=[{"name": "lint", "status": "failed", "error": "lint error"}],
            )

            assert event.type == "ci.validation_failed"
            assert event.metadata["stages"][0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_log_github_pr_event(self, audit_service):
        """Test logging GitHub PR event."""
        mock_event = MagicMock()
        mock_event.type = "github.pr_created"
        mock_event.action = "created"
        mock_event.metadata = {"pr_number": 42, "pr_url": "https://github.com/owner/repo/pull/42"}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_github_pr_event(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_type="human",
                actor_name="test_user",
                event_type="created",
                pr_number=42,
                pr_url="https://github.com/owner/repo/pull/42",
            )

            assert event.type == "github.pr_created"
            assert event.action == "created"
            assert event.metadata["pr_number"] == 42
            assert event.metadata["pr_url"] == "https://github.com/owner/repo/pull/42"


class TestAuditServiceEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_log_event_with_all_optional_fields(self):
        """Test logging event with all optional fields."""
        mock_event = MagicMock()
        mock_event.correlation_id = "corr-123"
        mock_event.causation_id = "cause-456"
        mock_event.before = {"content": "old"}
        mock_event.after = {"content": "new"}
        mock_event.metadata = {"confidence": 0.9}
        mock_event.insert = AsyncMock()

        with patch("pipelineiq.services.audit.IncidentEvent", return_value=mock_event):
            event = await AuditService().log_event(
                incident_id=PydanticObjectId(),
                workspace_id=PydanticObjectId(),
                actor_id=PydanticObjectId(),
                actor_type="ai",
                actor_name="AI Agent",
                event_type="ai.fix_proposed",
                action="suggest",
                description="Fix bug",
                document_id=PydanticObjectId(),
                version_id=PydanticObjectId(),
                before={"content": "old"},
                after={"content": "new"},
                metadata={"confidence": 0.9},
                correlation_id="corr-123",
                causation_id="cause-456",
            )

            assert event.correlation_id == "corr-123"
            assert event.causation_id is not None
            assert event.before == {"content": "old"}
            assert event.after == {"content": "new"}
            assert event.metadata["confidence"] == 0.9