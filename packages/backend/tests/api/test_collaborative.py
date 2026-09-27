"""Tests for Collaborative API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime
from beanie import PydanticObjectId


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.cookies = {"piq_session": "valid-token"}
    return request


@pytest.fixture
def mock_workspace():
    workspace = MagicMock()
    workspace.id = PydanticObjectId()
    workspace.workspace_id = "ws-123"
    workspace.incident_id = PydanticObjectId()
    workspace.repository_full_name = "owner/repo"
    workspace.base_branch = "main"
    workspace.head_branch = "feature/test"
    workspace.head_sha = "abc123"
    workspace.owner_id = PydanticObjectId()
    workspace.participants = []
    workspace.status = "active"
    workspace.created_at = datetime.now(UTC)
    workspace.updated_at = datetime.now(UTC)
    workspace.last_synced_at = None
    return workspace


@pytest.fixture
def mock_current_user():
    return PydanticObjectId()


class TestCollaborativeAPI:
    """Tests for collaborative workspace API endpoints."""

    @pytest.mark.asyncio
    async def test_create_workspace_success(self, mock_request, mock_current_user):
        """Test successful workspace creation."""
        mock_pipeline_run = MagicMock()
        mock_pipeline_run.id = PydanticObjectId()
        mock_pipeline_run.workspace_id = PydanticObjectId()
        mock_pipeline_run.repository_full_name = "owner/repo"
        mock_pipeline_run.branch = "main"
        mock_pipeline_run.commit_sha = "abc123"

        mock_new_workspace = MagicMock()
        mock_new_workspace.id = PydanticObjectId()
        mock_new_workspace.workspace_id = "ws-123"
        mock_new_workspace.incident_id = PydanticObjectId()
        mock_new_workspace.repository_full_name = "owner/repo"
        mock_new_workspace.base_branch = "main"
        mock_new_workspace.head_branch = "main"
        mock_new_workspace.head_sha = "abc123"
        mock_new_workspace.owner_id = mock_current_user
        mock_new_workspace.participants = []
        mock_new_workspace.status = "active"
        mock_new_workspace.created_at = datetime.now(UTC)
        mock_new_workspace.updated_at = datetime.now(UTC)
        mock_new_workspace.last_synced_at = None

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=mock_current_user):
            with patch("pipelineiq.models.PipelineRun.get", return_value=mock_pipeline_run):
                with patch("pipelineiq.models.CollaborativeWorkspace.find_one", return_value=None):
                    with patch("pipelineiq.models.CollaborativeWorkspace", return_value=mock_new_workspace):
                        with patch("pipelineiq.services.workspaces.create_collaborative_workspace", new_callable=AsyncMock, return_value=mock_new_workspace):
                            with patch("pipelineiq.services.workspaces.initialize_workspace_documents", new_callable=AsyncMock):
                                from pipelineiq.api.collaborative import create_workspace
                                result = await create_workspace(MagicMock(), MagicMock(incident_id=str(PydanticObjectId())))

                                assert result.workspace_id == "ws-123"
                                assert result.status == "active"

    @pytest.mark.asyncio
    async def test_create_workspace_already_exists(self, mock_request, mock_current_user):
        """Test workspace creation when already exists."""
        mock_pipeline_run = MagicMock()
        mock_pipeline_run.id = PydanticObjectId()
        mock_pipeline_run.workspace_id = PydanticObjectId()
        mock_pipeline_run.repository_full_name = "owner/repo"
        mock_pipeline_run.branch = "main"
        mock_pipeline_run.commit_sha = "abc123"

        mock_existing_workspace = MagicMock()
        mock_existing_workspace.id = PydanticObjectId()

        mock_new_workspace = MagicMock()
        mock_new_workspace.id = PydanticObjectId()
        mock_new_workspace.workspace_id = "ws-123"
        mock_new_workspace.incident_id = PydanticObjectId()
        mock_new_workspace.repository_full_name = "owner/repo"
        mock_new_workspace.base_branch = "main"
        mock_new_workspace.head_branch = "main"
        mock_new_workspace.head_sha = "abc123"
        mock_new_workspace.owner_id = mock_current_user
        mock_new_workspace.participants = []
        mock_new_workspace.status = "active"
        mock_new_workspace.created_at = datetime.now(UTC)
        mock_new_workspace.updated_at = datetime.now(UTC)
        mock_new_workspace.last_synced_at = None

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=mock_current_user):
            with patch("pipelineiq.models.PipelineRun.get", return_value=mock_pipeline_run):
                with patch("pipelineiq.models.CollaborativeWorkspace.find_one", return_value=mock_existing_workspace):
                    with patch("pipelineiq.models.CollaborativeWorkspace", return_value=mock_new_workspace):
                        with patch("pipelineiq.services.workspaces.create_collaborative_workspace", new_callable=AsyncMock, return_value=mock_new_workspace):
                            with patch("pipelineiq.services.workspaces.initialize_workspace_documents", new_callable=AsyncMock):
                                from pipelineiq.api.collaborative import create_workspace
                                result = await create_workspace(MagicMock(), MagicMock(incident_id=str(PydanticObjectId())))

                                assert result.workspace_id == "ws-123"

    @pytest.mark.asyncio
    async def test_create_workspace_not_found(self, mock_current_user):
        """Test workspace creation with non-existent pipeline run."""
        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=mock_current_user):
            with patch("pipelineiq.models.PipelineRun.get", return_value=None):
                from pipelineiq.api.collaborative import create_workspace
                try:
                    await create_workspace(MagicMock(), MagicMock(incident_id=str(PydanticObjectId())))
                    assert False, "Should have raised PipelineIQError"
                except Exception as e:
                    assert "PIPELINE_RUN_NOT_FOUND" in str(e)

    @pytest.mark.asyncio
    async def test_create_workspace_forbidden(self, mock_request, mock_current_user):
        """Test workspace creation with wrong owner."""
        other_user = PydanticObjectId()
        mock_pipeline_run = MagicMock()
        mock_pipeline_run.id = PydanticObjectId()
        mock_pipeline_run.workspace_id = other_user
        mock_pipeline_run.repository_full_name = "owner/repo"
        mock_pipeline_run.branch = "main"
        mock_pipeline_run.commit_sha = "abc123"

        mock_workspace = MagicMock()
        mock_workspace.owner_id = other_user

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=mock_current_user):
            with patch("pipelineiq.models.PipelineRun.get", return_value=MagicMock(workspace_id=other_user)):
                with patch("pipelineiq.models.Workspace.get", return_value=MagicMock(owner_id=other_user)):
                    from pipelineiq.api.collaborative import create_workspace
                    try:
                        await create_workspace(MagicMock(), MagicMock(incident_id=str(PydanticObjectId())))
                        assert False, "Should have raised PipelineIQError"
                    except Exception as e:
                        assert "FORBIDDEN" in str(e)

    @pytest.mark.asyncio
    async def test_get_workspace(self, mock_current_user, mock_workspace):
        """Test getting workspace by ID."""
        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=mock_current_user):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                from pipelineiq.api.collaborative import get_workspace
                result = await get_workspace(MagicMock(), "ws-123")
                assert result.workspace_id == "ws-123"

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, mock_current_user):
        """Test getting non-existent workspace."""
        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=mock_current_user):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", side_effect=Exception("Not found")):
                from pipelineiq.api.collaborative import get_workspace
                try:
                    await get_workspace(MagicMock(), "ws-999")
                    assert False, "Should have raised PipelineIQError"
                except Exception as e:
                    assert "WORKSPACE_NOT_FOUND" in str(e)


class TestDocumentOperations:
    """Tests for document CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_documents(self, mock_current_user, mock_workspace):
        """Test listing workspace documents."""
        mock_doc = MagicMock()
        mock_doc.id = PydanticObjectId()
        mock_doc.workspace_id = mock_workspace.id
        mock_doc.path = "src/main.py"
        mock_doc.language = "python"
        mock_doc.content = "print('hello')"
        mock_doc.original_content = "print('hello')"
        mock_doc.version = 1
        mock_doc.last_modified_by = PydanticObjectId()
        mock_doc.last_modified_at = datetime.now(UTC)
        mock_doc.is_binary = False

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=MagicMock(id=PydanticObjectId())):
                with patch("pipelineiq.models.WorkspaceDocument.find", return_value=[MagicMock()]):
                    from pipelineiq.api.collaborative import list_documents
                    result = await list_documents(MagicMock(), "ws-123")
                    assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_document(self, mock_current_user, mock_workspace):
        """Test updating a document."""
        mock_doc = MagicMock()
        mock_doc.id = PydanticObjectId()
        mock_doc.workspace_id = mock_workspace.id
        mock_doc.path = "src/main.py"
        mock_doc.content = "print('hello')"
        mock_doc.original_content = "print('hello')"
        mock_doc.version = 1
        mock_doc.last_modified_by = PydanticObjectId()
        mock_doc.last_modified_at = datetime.now(UTC)
        mock_doc.is_binary = False

        mock_updated_doc = MagicMock()
        mock_updated_doc.id = PydanticObjectId()
        mock_updated_doc.workspace_id = PydanticObjectId()
        mock_updated_doc.path = "src/main.py"
        mock_updated_doc.language = "python"
        mock_updated_doc.content = "print('updated')"
        mock_updated_doc.original_content = "print('hello')"
        mock_updated_doc.version = 2
        mock_updated_doc.last_modified_by = PydanticObjectId()
        mock_updated_doc.last_modified_at = datetime.now(UTC)
        mock_updated_doc.is_binary = False

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.models.WorkspaceDocument.find_one", return_value=MagicMock(id=PydanticObjectId())):
                    with patch("pipelineiq.models.WorkspaceDocument", return_value=mock_updated_doc):
                        with patch("pipelineiq.services.workspaces.update_workspace_document", new_callable=AsyncMock, return_value=mock_updated_doc):
                            from pipelineiq.api.collaborative import update_document
                            result = await update_document(MagicMock(), "ws-123", "src/main.py", {"content": "print('updated')"})
                            assert result.content == "print('updated')"

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, mock_current_user, mock_workspace):
        """Test creating a document checkpoint."""
        mock_doc = MagicMock()
        mock_doc.id = PydanticObjectId()
        mock_doc.workspace_id = mock_workspace.id
        mock_doc.path = "src/main.py"

        mock_version = MagicMock()
        mock_version.id = PydanticObjectId()
        mock_version.workspace_id = mock_workspace.id
        mock_version.document_id = mock_doc.id
        mock_version.version_number = 1
        mock_version.parent_version_id = None
        mock_version.content_snapshot = "print('hello')"
        mock_version.operations = []
        mock_version.author_id = PydanticObjectId()
        mock_version.author_type = "human"
        mock_version.message = "Initial commit"
        mock_version.tags = ["initial"]
        mock_version.ci_run_id = None
        mock_version.ci_status = None
        mock_version.ci_url = None
        mock_version.created_at = datetime.now(UTC)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.models.WorkspaceDocument.find_one", return_value=MagicMock(id=PydanticObjectId())):
                    with patch("pipelineiq.models.DocumentVersion", return_value=mock_version):
                        with patch("pipelineiq.services.workspaces.create_document_version", new_callable=AsyncMock, return_value=mock_version):
                            from pipelineiq.api.collaborative import create_checkpoint
                            result = await create_checkpoint(MagicMock(), "ws-123", "src/main.py", MagicMock(message="Initial commit", tags=["initial"]))
                            assert result.version_number == 1


class TestVersionOperations:
    """Tests for version history operations."""

    @pytest.mark.asyncio
    async def test_list_versions(self, mock_current_user, mock_workspace):
        """Test listing document versions."""
        mock_doc = MagicMock()
        mock_doc.id = PydanticObjectId()
        mock_doc.workspace_id = mock_workspace.id

        mock_version = MagicMock()
        mock_version.id = PydanticObjectId()
        mock_version.workspace_id = mock_workspace.id
        mock_version.document_id = PydanticObjectId()
        mock_version.version_number = 1
        mock_version.parent_version_id = None
        mock_version.content_snapshot = "content"
        mock_version.operations = []
        mock_version.author_id = PydanticObjectId()
        mock_version.author_type = "human"
        mock_version.message = "Initial"
        mock_version.tags = []
        mock_version.ci_run_id = None
        mock_version.ci_status = None
        mock_version.ci_url = None
        mock_version.created_at = datetime.now(UTC)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.models.WorkspaceDocument.find_one", return_value=MagicMock(id=PydanticObjectId())):
                    with patch("pipelineiq.services.workspaces.get_document_versions", return_value=[MagicMock()]):
                        from pipelineiq.api.collaborative import list_versions
                        result = await list_versions(MagicMock(), "ws-123", "src/main.py")
                        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_restore_version(self, mock_current_user, mock_workspace):
        """Test restoring a document to a previous version."""
        mock_doc = MagicMock()
        mock_doc.id = PydanticObjectId()
        mock_doc.workspace_id = mock_workspace.id

        mock_restored = MagicMock()
        mock_restored.id = PydanticObjectId()
        mock_restored.workspace_id = mock_workspace.id
        mock_restored.path = "src/main.py"
        mock_restored.content = "old content"
        mock_restored.original_content = "old content"
        mock_restored.version = 2
        mock_restored.last_modified_by = PydanticObjectId()
        mock_restored.last_modified_at = datetime.now(UTC)
        mock_restored.is_binary = False

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.models.WorkspaceDocument.find_one", return_value=MagicMock(id=PydanticObjectId())):
                    with patch("pipelineiq.models.WorkspaceDocument", return_value=mock_restored):
                        with patch("pipelineiq.services.workspaces.restore_document_version", new_callable=AsyncMock, return_value=mock_restored):
                            from pipelineiq.api.collaborative import restore_version
                            result = await restore_version(MagicMock(), "ws-123", "src/main.py", MagicMock(version_id=str(PydanticObjectId())))
                            assert result.content == "old content"


class TestValidationEndpoints:
    """Tests for validation endpoints."""

    @pytest.mark.asyncio
    async def test_start_validation(self, mock_current_user, mock_workspace):
        """Test starting a validation run."""
        mock_doc = MagicMock()
        mock_doc.id = PydanticObjectId()
        mock_doc.workspace_id = mock_workspace.id

        mock_version = MagicMock()
        mock_version.id = PydanticObjectId()
        mock_version.workspace_id = mock_workspace.id
        mock_version.document_id = PydanticObjectId()
        mock_version.version_number = 1

        mock_validation = MagicMock()
        mock_validation.id = PydanticObjectId()
        mock_validation.workspace_id = PydanticObjectId()
        mock_validation.version_id = PydanticObjectId()
        mock_validation.triggered_by = PydanticObjectId()
        mock_validation.status = "pending"
        mock_validation.stages = []
        mock_validation.started_at = None
        mock_validation.completed_at = None
        mock_validation.logs = []
        mock_validation.created_at = datetime.now(UTC)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.models.WorkspaceDocument.find", return_value=[MagicMock(id=PydanticObjectId())]):
                    with patch("pipelineiq.models.DocumentVersion.find", return_value=MagicMock(sort=MagicMock(return_value=MagicMock(first_or_none=AsyncMock(return_value=MagicMock(id=PydanticObjectId())))))):
                        with patch("pipelineiq.models.ValidationRun", return_value=mock_validation):
                            with patch("pipelineiq.services.workspaces.start_validation_run", new_callable=AsyncMock, return_value=mock_validation):
                                from pipelineiq.api.collaborative import start_validation
                                result = await start_validation(MagicMock(), "ws-123", {})
                                assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_start_validation_with_version(self, mock_current_user, mock_workspace):
        """Test starting validation with specific version."""
        mock_version = MagicMock()
        mock_version.id = PydanticObjectId()

        mock_validation = MagicMock()
        mock_validation.id = PydanticObjectId()
        mock_validation.workspace_id = PydanticObjectId()
        mock_validation.version_id = PydanticObjectId()
        mock_validation.triggered_by = PydanticObjectId()
        mock_validation.status = "pending"
        mock_validation.stages = []
        mock_validation.started_at = None
        mock_validation.completed_at = None
        mock_validation.logs = []
        mock_validation.created_at = datetime.now(UTC)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.models.DocumentVersion.find", return_value=MagicMock(sort=MagicMock(return_value=MagicMock(first_or_none=AsyncMock(return_value=MagicMock(id=PydanticObjectId())))))):
                    with patch("pipelineiq.models.ValidationRun", return_value=mock_validation):
                        with patch("pipelineiq.services.workspaces.start_validation_run", new_callable=AsyncMock, return_value=mock_validation):
                            from pipelineiq.api.collaborative import start_validation
                            result = await start_validation(MagicMock(), "ws-123", {"version_id": str(PydanticObjectId())})
                            assert result.status == "pending"


class TestTimelineEndpoints:
    """Tests for timeline/audit endpoints."""

    @pytest.mark.asyncio
    async def test_get_timeline(self, mock_current_user, mock_workspace):
        """Test getting incident timeline."""
        mock_event = MagicMock()
        mock_event.id = PydanticObjectId()
        mock_event.incident_id = PydanticObjectId()
        mock_event.workspace_id = mock_workspace.id
        mock_event.actor_id = PydanticObjectId()
        mock_event.actor_type = "human"
        mock_event.actor_name = "test_user"
        mock_event.type = "workspace.document_edited"
        mock_event.action = "edit"
        mock_event.description = "Modified file"
        mock_event.document_id = None
        mock_event.version_id = None
        mock_event.before = {}
        mock_event.after = {}
        mock_event.metadata = {}
        mock_event.correlation_id = None
        mock_event.causation_id = None
        mock_event.timestamp = datetime.now(UTC)

        # Mock the query chain: find() -> sort() -> limit() -> to_list()
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[mock_event])

        mock_incident_event_class = MagicMock()
        mock_incident_event_class.find = MagicMock(return_value=mock_query)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.api.collaborative.IncidentEvent", mock_incident_event_class):
                    from pipelineiq.api.collaborative import get_timeline
                    result = await get_timeline(MagicMock(), "ws-123")
                    assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_timeline_with_filters(self, mock_current_user, mock_workspace):
        """Test getting timeline with filters (no filters currently supported in API)."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])

        mock_incident_event_class = MagicMock()
        mock_incident_event_class.find = MagicMock(return_value=mock_query)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                with patch("pipelineiq.api.collaborative.IncidentEvent", mock_incident_event_class):
                    from pipelineiq.api.collaborative import get_timeline
                    result = await get_timeline(MagicMock(), "ws-123")
                    assert isinstance(result, list)


class TestSyncStatus:
    """Tests for sync status endpoint."""

    @pytest.mark.asyncio
    async def test_get_sync_status(self, mock_current_user, mock_workspace):
        """Test getting sync status."""
        mock_workspace.last_synced_at = datetime.now(UTC)

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                from pipelineiq.api.collaborative import get_sync_status
                result = await get_sync_status(MagicMock(), "ws-123")

                assert result["status"] == "online"
                assert result["workspace_id"] == "ws-123"
                assert "last_synced_at" in result

    @pytest.mark.asyncio
    async def test_get_sync_status_offline(self, mock_current_user, mock_workspace):
        """Test sync status when offline."""
        mock_workspace.last_synced_at = None

        with patch("pipelineiq.api.collaborative.require_owner_id", return_value=PydanticObjectId()):
            with patch("pipelineiq.api.collaborative.get_workspace_or_404", return_value=mock_workspace):
                from pipelineiq.api.collaborative import get_sync_status
                result = await get_sync_status(MagicMock(), "ws-123")

                assert result["status"] == "offline"
                assert result["last_synced_at"] is None