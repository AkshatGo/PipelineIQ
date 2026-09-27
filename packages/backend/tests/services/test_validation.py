"""Tests for ValidationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime
from beanie import PydanticObjectId

from pipelineiq.services.validation import ValidationService
from pipelineiq.models import ValidationRun


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.GITHUB_API_URL = "https://api.github.com"
    return settings


@pytest.fixture
def mock_github_client():
    client = AsyncMock()
    client.create_file = AsyncMock(return_value={"content": {"path": ".github/workflows/test.yml"}})
    client.dispatch_workflow = AsyncMock(return_value={"status": "dispatched"})
    client.get_workflow_runs = AsyncMock(return_value=[])
    return client


@pytest.fixture
def validation_service(mock_settings, mock_github_client):
    with patch("pipelineiq.services.validation.GitHubAppClient", return_value=mock_github_client):
        service = ValidationService(mock_settings)
        service.client = mock_github_client
        return service


@pytest.fixture
def sample_workspace_id():
    return PydanticObjectId()


@pytest.fixture
def sample_version_id():
    return PydanticObjectId()


@pytest.fixture
def sample_user_id():
    return PydanticObjectId()


class TestValidationService:
    """Tests for ValidationService class."""

    @pytest.mark.asyncio
    async def test_create_workflow_file_default_stages(self, validation_service, sample_workspace_id):
        """Test workflow file generation with default stages."""
        workflow = await validation_service.create_workflow_file(sample_workspace_id)

        assert "name: PipelineIQ Validation" in workflow
        assert "workflow_dispatch" in workflow
        assert "validation_run_id" in workflow
        assert "lint" in workflow
        assert "typecheck" in workflow
        assert "test" in workflow
        assert "build" in workflow
        assert "actions/checkout@v4" in workflow
        assert "actions/setup-node@v4" in workflow
        assert "npm ci" in workflow
        assert "npm run lint" in workflow
        assert "npm run typecheck" in workflow
        assert "npm test" in workflow
        assert "npm run build" in workflow
        assert "actions/upload-artifact@v4" in workflow

    @pytest.mark.asyncio
    async def test_create_workflow_file_custom_stages(self, validation_service, sample_workspace_id):
        """Test workflow file generation with custom stages."""
        custom_stages = [
            {"name": "custom", "command": "npm run custom", "required": True, "timeout": 30000},
        ]
        workflow = await validation_service.create_workflow_file(sample_workspace_id, custom_stages)

        assert "custom" in workflow
        assert "npm run custom" in workflow
        assert "timeout-minutes: 0" in workflow  # 30000 // 60000 = 0

    @pytest.mark.asyncio
    async def test_create_workflow_file_timeout_calculation(self, validation_service, sample_workspace_id):
        """Test timeout calculation for stages."""
        stages = [
            {"name": "fast", "command": "npm run fast", "timeout": 30000},  # 0 min
            {"name": "slow", "command": "npm run slow", "timeout": 120000},  # 2 min
        ]
        workflow = await validation_service.create_workflow_file(sample_workspace_id, stages)

        assert "timeout-minutes: 0" in workflow  # 30000 // 60000 = 0
        assert "timeout-minutes: 2" in workflow  # 120000 // 60000 = 2

    @pytest.mark.asyncio
    async def test_trigger_validation_no_workspace(self, validation_service):
        """Test trigger_validation when workspace not found."""
        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=None):
            result = await validation_service.trigger_validation(
                MagicMock(workspace_id=PydanticObjectId()),
                PydanticObjectId(),
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_trigger_validation_no_installation(self, validation_service):
        """Test trigger_validation when workspace has no GitHub installation."""
        mock_workspace = MagicMock()
        mock_workspace.github_installation_id = None

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            result = await validation_service.trigger_validation(
                MagicMock(workspace_id=PydanticObjectId()),
                PydanticObjectId(),
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_trigger_validation_success(self, validation_service, sample_workspace_id):
        """Test successful validation trigger."""
        mock_workspace = MagicMock()
        mock_workspace.id = sample_workspace_id
        mock_workspace.github_installation_id = 12345
        mock_workspace.repository_full_name = "owner/repo"
        mock_workspace.head_branch = "main"

        mock_validation_run = MagicMock()
        mock_validation_run.id = PydanticObjectId()
        mock_validation_run.workspace_id = PydanticObjectId()

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            with patch.object(validation_service, "create_workflow_file", return_value="workflow yaml"):
                result = await validation_service.trigger_validation(
                    MagicMock(workspace_id=sample_workspace_id),
                    PydanticObjectId(),
                )

            assert result == {"status": "dispatched"}

    @pytest.mark.asyncio
    async def test_trigger_validation_exception(self, validation_service, sample_workspace_id):
        """Test trigger_validation when exception occurs."""
        mock_workspace = MagicMock()
        mock_workspace.id = sample_workspace_id
        mock_workspace.github_installation_id = 12345
        mock_workspace.repository_full_name = "owner/repo"
        mock_workspace.head_branch = "main"

        mock_client = MagicMock()
        mock_client.create_file = AsyncMock(side_effect=Exception("API Error"))

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            with patch.object(validation_service, "create_workflow_file", return_value="workflow yaml"):
                validation_service.client = MagicMock()
                validation_service.client.create_file = AsyncMock(side_effect=Exception("API Error"))

                result = await validation_service.trigger_validation(
                    MagicMock(workspace_id=sample_workspace_id),
                    PydanticObjectId(),
                )

            assert result is None

    @pytest.mark.asyncio
    async def test_poll_validation_status_no_workspace(self, validation_service):
        """Test poll_validation_status when workspace not found."""
        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=None):
            result = await validation_service.poll_validation_status(
                MagicMock(workspace_id=PydanticObjectId()),
            )
            assert result == {"status": "error", "error": "No GitHub installation"}

    @pytest.mark.asyncio
    async def test_poll_validation_status_no_installation(self, validation_service):
        """Test poll when workspace has no GitHub installation."""
        mock_workspace = MagicMock()
        mock_workspace.github_installation_id = None

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            result = await validation_service.poll_validation_status(MagicMock(workspace_id=PydanticObjectId()))
            assert result == {"status": "error", "error": "No GitHub installation"}

    @pytest.mark.asyncio
    async def test_poll_validation_status_success(self, validation_service):
        """Test successful validation polling."""
        mock_workspace = MagicMock()
        mock_workspace.github_installation_id = 12345
        mock_workspace.repository_full_name = "owner/repo"
        mock_workspace.head_branch = "main"

        mock_run = {"conclusion": "success", "id": 123, "html_url": "https://github.com/owner/repo/actions/runs/123"}

        mock_client = AsyncMock()
        mock_client.get_workflow_runs = AsyncMock(return_value=[mock_run])

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            validation_service.client = mock_client
            result = await validation_service.poll_validation_status(
                MagicMock(workspace_id=PydanticObjectId(), id=PydanticObjectId()),
                max_wait_seconds=10,
                poll_interval=1,
            )

            assert result["status"] == "success"
            assert result["run_id"] == 123

    @pytest.mark.asyncio
    async def test_poll_validation_status_failure(self, validation_service):
        """Test validation polling with failure result."""
        mock_workspace = MagicMock()
        mock_workspace.github_installation_id = 12345
        mock_workspace.repository_full_name = "owner/repo"
        mock_workspace.head_branch = "main"

        mock_run = {"conclusion": "failure", "id": 123, "html_url": "https://github.com/owner/repo/actions/runs/123"}

        mock_client = AsyncMock()
        mock_client.get_workflow_runs = AsyncMock(return_value=[mock_run])

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            validation_service.client = mock_client
            result = await validation_service.poll_validation_status(
                MagicMock(workspace_id=PydanticObjectId(), id=PydanticObjectId()),
                max_wait_seconds=10,
                poll_interval=1,
            )

            assert result["status"] == "failure"

    @pytest.mark.asyncio
    async def test_poll_validation_status_timeout(self, validation_service):
        """Test validation polling timeout."""
        mock_workspace = MagicMock()
        mock_workspace.github_installation_id = 12345
        mock_workspace.repository_full_name = "owner/repo"
        mock_workspace.head_branch = "main"

        mock_client = AsyncMock()
        mock_client.get_workflow_runs = AsyncMock(return_value=[])

        with patch("pipelineiq.services.validation.get_collaborative_workspace_by_incident", return_value=mock_workspace):
            validation_service.client = AsyncMock()
            validation_service.client.get_workflow_runs = AsyncMock(return_value=[])
            result = await validation_service.poll_validation_status(
                MagicMock(workspace_id=PydanticObjectId(), id=PydanticObjectId()),
                max_wait_seconds=1,
                poll_interval=1,
            )

            assert result["status"] == "timeout"


class TestValidationRunPipeline:
    """Tests for run_validation_pipeline method."""

    @pytest.mark.asyncio
    async def test_run_validation_pipeline_no_workspace(self, validation_service, sample_workspace_id):
        """Test pipeline when workspace not found."""
        with patch("pipelineiq.models.CollaborativeWorkspace.get", return_value=None):
            with patch("pipelineiq.models.ValidationRun") as mock_validation_run_class:
                mock_validation_run = MagicMock()
                mock_validation_run.insert = AsyncMock()
                mock_validation_run.save = AsyncMock()
                mock_validation_run.status = "failed"
                mock_validation_run_class.return_value = mock_validation_run
                
                with patch("pipelineiq.services.audit.get_audit_service") as mock_audit:
                    mock_audit.return_value.log_validation_completed = AsyncMock()
                    result = await validation_service.run_validation_pipeline(
                        sample_workspace_id, PydanticObjectId(), PydanticObjectId()
                    )
            assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_run_validation_pipeline_dispatch_failed(self, validation_service):
        """Test pipeline when dispatch fails."""
        mock_workspace = MagicMock()
        mock_workspace.id = PydanticObjectId()
        mock_workspace.github_installation_id = 12345

        mock_validation_run = MagicMock()
        mock_validation_run.status = "failed"
        mock_validation_run.insert = AsyncMock()
        mock_validation_run.save = AsyncMock()
        mock_validation_run.workspace_id = mock_workspace.id
        mock_validation_run.triggered_by = PydanticObjectId()
        mock_validation_run.id = PydanticObjectId()

        mock_audit = MagicMock()
        mock_audit.log_validation_completed = AsyncMock()

        with patch("pipelineiq.models.CollaborativeWorkspace.get", return_value=mock_workspace):
            with patch.object(validation_service, "trigger_validation", return_value=None):
                with patch("pipelineiq.models.ValidationRun", return_value=mock_validation_run):
                    with patch("pipelineiq.services.validation.get_audit_service", return_value=mock_audit):
                        result = await validation_service.run_validation_pipeline(
                            PydanticObjectId(), PydanticObjectId(), PydanticObjectId()
                        )

                        assert result.status == "failed"
                        mock_audit.log_validation_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_validation_pipeline_success(self, validation_service):
        """Test successful validation pipeline."""
        mock_workspace = MagicMock()
        mock_workspace.id = PydanticObjectId()
        mock_workspace.github_installation_id = 12345
        mock_workspace.repository_full_name = "owner/repo"
        mock_workspace.head_branch = "main"

        mock_validation_run = MagicMock()
        mock_validation_run.status = "passed"
        mock_validation_run.insert = AsyncMock()
        mock_validation_run.save = AsyncMock()
        mock_validation_run.workspace_id = mock_workspace.id
        mock_validation_run.triggered_by = PydanticObjectId()
        mock_validation_run.id = PydanticObjectId()

        mock_audit = MagicMock()
        mock_audit.log_validation_completed = AsyncMock()

        with patch("pipelineiq.models.CollaborativeWorkspace.get", return_value=mock_workspace):
            with patch.object(validation_service, "trigger_validation", return_value={"status": "dispatched"}):
                with patch.object(validation_service, "poll_validation_status", return_value={"status": "success"}):
                    with patch("pipelineiq.models.ValidationRun", return_value=mock_validation_run):
                        with patch("pipelineiq.services.validation.get_audit_service", return_value=mock_audit):
                            result = await validation_service.run_validation_pipeline(
                                PydanticObjectId(), PydanticObjectId(), PydanticObjectId()
                            )

                            assert result.status == "passed"
                            mock_audit.log_validation_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_validation_pipeline_failure(self, validation_service):
        """Test pipeline with failed validation."""
        mock_workspace = MagicMock()
        mock_workspace.id = PydanticObjectId()
        mock_workspace.github_installation_id = 12345

        mock_validation_run = MagicMock()
        mock_validation_run.status = "failed"
        mock_validation_run.insert = AsyncMock()
        mock_validation_run.save = AsyncMock()
        mock_validation_run.workspace_id = mock_workspace.id
        mock_validation_run.triggered_by = PydanticObjectId()
        mock_validation_run.id = PydanticObjectId()

        mock_audit = MagicMock()
        mock_audit.log_validation_completed = AsyncMock()

        with patch("pipelineiq.models.CollaborativeWorkspace.get", return_value=mock_workspace):
            with patch.object(validation_service, "trigger_validation", return_value={"status": "dispatched"}):
                with patch.object(validation_service, "poll_validation_status", return_value={"status": "failure"}):
                    with patch("pipelineiq.models.ValidationRun", return_value=mock_validation_run):
                        with patch("pipelineiq.services.validation.get_audit_service", return_value=mock_audit):
                            result = await validation_service.run_validation_pipeline(
                                PydanticObjectId(), PydanticObjectId(), PydanticObjectId()
                            )

                            assert result.status == "failed"
                            mock_audit.log_validation_completed.assert_called_once()