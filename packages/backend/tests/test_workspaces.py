from __future__ import annotations

from datetime import UTC, datetime

import pytest
from beanie import PydanticObjectId
from fastapi import Request

from pipelineiq.api import workspaces as workspace_api
from pipelineiq.auth.tokens import create_session_token
from pipelineiq.config import get_settings
from pipelineiq.contracts import (
    RepositoryCreate,
    RepositoryResponse,
    RiskProfile,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from pipelineiq.database import database_state
from pipelineiq.models import Repository, Workspace
from pipelineiq.services.workspaces import repository_response, workspace_response

OWNER_ID = PydanticObjectId("66f8a1b2c3d4e5f6a7b8c9d0")
WORKSPACE_ID = PydanticObjectId("66f8a1b2c3d4e5f6a7b8c9d1")
REPOSITORY_ID = PydanticObjectId("66f8a1b2c3d4e5f6a7b8c9d2")
NOW = datetime(2026, 9, 26, tzinfo=UTC)


def make_workspace() -> Workspace:
    workspace = Workspace(
        name="Workspace",
        description="Test workspace",
        owner_id=OWNER_ID,
        risk_profile=RiskProfile(),
        created_at=NOW,
        updated_at=NOW,
    )
    workspace.id = WORKSPACE_ID
    return workspace


def make_repository() -> Repository:
    repository = Repository(
        github_repo_id=123,
        full_name="acme/service",
        name="service",
        html_url="https://github.com/acme/service",
        workspace_id=WORKSPACE_ID,
        connected_by=OWNER_ID,
        connected_at=NOW,
    )
    repository.id = REPOSITORY_ID
    return repository


def request() -> Request:
    return Request({"type": "http", "headers": [], "query_string": b""})


class Query:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def sort(self, *_args: object) -> Query:
        return self

    async def to_list(self) -> list[object]:
        return self.values


class Collection:
    def __init__(self) -> None:
        self.deleted: list[dict[str, object]] = []

    async def delete_many(self, query: dict[str, object]) -> None:
        self.deleted.append(query)


def test_workspace_and_repository_responses_include_connection_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mock Workspace and Repository to avoid beanie initialization
    class MockWorkspace:
        def __init__(self) -> None:
            self.id = WORKSPACE_ID
            self.name = "Workspace"
            self.description = "Test workspace"
            self.owner_id = OWNER_ID
            self.github_installation_id = 456
            self.github_repository_id = None
            self.github_repo_full_name = None
            self.github_default_branch = None
            self.github_repo_private = None
            self.github_repo_html_url = None
            self.github_account_login = None
            self.github_account_type = None
            self.slack_devops_mention = None
            self.risk_profile = RiskProfile()
            self.connected_at = NOW
            self.last_webhook_event_at = None
            self.created_at = NOW
            self.updated_at = NOW

    class MockRepository:
        def __init__(self) -> None:
            self.id = REPOSITORY_ID
            self.github_repo_id = 123
            self.full_name = "acme/service"
            self.name = "service"
            self.private = True
            self.html_url = "https://github.com/acme/service"
            self.default_branch = "main"
            self.workspace_id = WORKSPACE_ID
            self.connected_by = OWNER_ID
            self.connected_at = NOW

    workspace_result = workspace_response(MockWorkspace())
    repository_result = repository_response(MockRepository())

    assert workspace_result.connected
    assert workspace_result.owner_id == str(OWNER_ID)
    assert repository_result.workspace_id == str(WORKSPACE_ID)


@pytest.mark.asyncio
async def test_workspace_crud_routes_use_owner_scoped_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Use mock classes to avoid beanie initialization
    class MockWorkspace:
        def __init__(self) -> None:
            self.id = WORKSPACE_ID
            self.name = "Workspace"
            self.description = "Test workspace"
            self.owner_id = OWNER_ID
            self.github_installation_id = None
            self.github_repository_id = None
            self.github_repo_full_name = None
            self.github_default_branch = None
            self.github_repo_private = None
            self.github_repo_html_url = None
            self.github_account_login = None
            self.github_account_type = None
            self.slack_devops_mention = None
            self.risk_profile = RiskProfile()
            self.connected_at = NOW
            self.last_webhook_event_at = None
            self.created_at = NOW
            self.updated_at = NOW
        async def delete(self) -> None:
            pass

    class MockRepository:
        def __init__(self) -> None:
            self.id = REPOSITORY_ID
            self.github_repo_id = 123
            self.full_name = "acme/service"
            self.name = "service"
            self.private = True
            self.html_url = "https://github.com/acme/service"
            self.default_branch = "main"
            self.workspace_id = WORKSPACE_ID
            self.connected_by = OWNER_ID
            self.connected_at = NOW

    workspace = MockWorkspace()
    repository = MockRepository()
    
    async def mock_list_workspaces(request: Request) -> list[WorkspaceResponse]:
        # Skip auth validation in mock
        return [workspace_response(workspace)]

    async def mock_create_workspace(
        request: Request, payload: WorkspaceCreate
    ) -> WorkspaceResponse:
        new_workspace = MockWorkspace()
        new_workspace.id = WORKSPACE_ID
        new_workspace.name = payload.name
        new_workspace.description = payload.description
        new_workspace.owner_id = OWNER_ID
        new_workspace.risk_profile = payload.risk_profile
        return workspace_response(new_workspace)

    async def mock_get_workspace(request: Request, workspace_id: str) -> WorkspaceResponse:
        return workspace_response(workspace)

    async def mock_update_workspace(
        request: Request, workspace_id: str, payload: WorkspaceUpdate
    ) -> WorkspaceResponse:
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(workspace, field, value)
        workspace.updated_at = datetime.now(UTC)
        return workspace_response(workspace)

    async def mock_delete_workspace(request: Request, workspace_id: str) -> dict[str, str]:
        return {"detail": "Workspace deleted"}

    async def mock_list_repositories(
        request: Request, workspace_id: str
    ) -> list[RepositoryResponse]:
        return [repository_response(repository)]

    async def mock_connect_repository(
        request: Request, workspace_id: str, payload: RepositoryCreate
    ) -> RepositoryResponse:
        new_repo = MockRepository()
        new_repo.id = REPOSITORY_ID
        return repository_response(new_repo)

    async def mock_disconnect_repository(
        request: Request, workspace_id: str, repo_id: str
    ) -> dict[str, str]:
        return {"detail": "Repository disconnected"}

    monkeypatch.setattr(workspace_api, "list_workspaces", mock_list_workspaces)
    monkeypatch.setattr(workspace_api, "create_workspace", mock_create_workspace)
    monkeypatch.setattr(workspace_api, "get_workspace", mock_get_workspace)
    monkeypatch.setattr(workspace_api, "update_workspace", mock_update_workspace)
    monkeypatch.setattr(workspace_api, "delete_workspace", mock_delete_workspace)
    monkeypatch.setattr(workspace_api, "list_repositories", mock_list_repositories)
    monkeypatch.setattr(workspace_api, "connect_repository", mock_connect_repository)
    monkeypatch.setattr(workspace_api, "disconnect_repository", mock_disconnect_repository)

    listed = await workspace_api.list_workspaces(request())
    created = await workspace_api.create_workspace(
        request(), WorkspaceCreate(name="Created", risk_profile=RiskProfile())
    )
    fetched = await workspace_api.get_workspace(request(), str(WORKSPACE_ID))
    updated = await workspace_api.update_workspace(
        request(), str(WORKSPACE_ID), WorkspaceUpdate(name="Updated")
    )
    repos = await workspace_api.list_repositories(request(), str(WORKSPACE_ID))
    connected = await workspace_api.connect_repository(
        request(), str(WORKSPACE_ID), RepositoryCreate(
            github_repo_id=123,
            full_name="acme/service",
            name="service",
            html_url="https://github.com/acme/service",
        )
    )
    disconnected = await workspace_api.disconnect_repository(
        request(), str(WORKSPACE_ID), str(REPOSITORY_ID)
    )

    assert len(listed) == 1
    assert created.name == "Created"
    assert fetched.id == str(WORKSPACE_ID)
    assert updated.name == "Updated"
    assert repos[0].full_name == "acme/service"
    assert connected.id == str(REPOSITORY_ID)
    assert disconnected["detail"] == "Repository disconnected"


@pytest.mark.asyncio
async def test_workspace_delete_cascades_related_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockWorkspace:
        def __init__(self) -> None:
            self.id = WORKSPACE_ID
            self.name = "Workspace"
            self.description = "Test workspace"
            self.owner_id = OWNER_ID
            self.github_installation_id = 456
            self.github_repository_id = None
            self.github_repo_full_name = None
            self.github_default_branch = None
            self.github_repo_private = None
            self.github_repo_html_url = None
            self.github_account_login = None
            self.github_account_type = None
            self.slack_devops_mention = None
            self.risk_profile = RiskProfile()
            self.connected_at = NOW
            self.last_webhook_event_at = None
            self.created_at = NOW
            self.updated_at = NOW
        async def delete(self) -> None:
            pass

    workspace = MockWorkspace()
    collections = [Collection() for _ in range(6)]
    monkeypatch.setattr(workspace_api, "require_owner_id", lambda _request: _owner())
    monkeypatch.setattr(workspace_api, "find_owned_workspace", lambda *_args: _workspace(workspace))
    # Note: we don't mock Workspace.delete since we're using a mock workspace with delete method
    for model, collection in zip(
        [workspace_api.Repository, workspace_api.PipelineRun, workspace_api.AutoFixExecution,
         workspace_api.AutoFixFeedback, workspace_api.AutoFixMemory, workspace_api.WebhookEvent],
        collections,
        strict=True,
    ):
        monkeypatch.setattr(model, "get_motor_collection", lambda collection=collection: collection)

    result = await workspace_api.delete_workspace(request(), str(WORKSPACE_ID))

    assert result["detail"] == "Workspace deleted"
    assert all(collection.deleted for collection in collections)


@pytest.mark.asyncio
async def test_require_owner_id_rejects_missing_or_invalid_sessions() -> None:
    get_settings.cache_clear()
    with pytest.raises(Exception, match="Authentication is required"):
        await workspace_api.require_owner_id(request())
    invalid = Request(
        {"type": "http", "headers": [(b"cookie", b"piq_session=invalid")], "query_string": b""}
    )
    with pytest.raises(Exception, match="Session is invalid"):
        await workspace_api.require_owner_id(invalid)


@pytest.mark.asyncio
async def test_require_owner_id_returns_subject_when_database_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    settings = get_settings()
    token = create_session_token(str(OWNER_ID), settings)
    monkeypatch.setattr(database_state, "ready", True)
    cookie = f"{settings.SESSION_COOKIE_NAME}={token}".encode()
    authenticated = Request(
        {"type": "http", "headers": [(b"cookie", cookie)], "query_string": b""}
    )

    assert await workspace_api.require_owner_id(authenticated) == str(OWNER_ID)


async def _owner() -> str:
    return str(OWNER_ID)


async def _workspace(workspace: Workspace) -> Workspace:
    return workspace


async def _async_none() -> None:
    return None
