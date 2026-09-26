from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Request, status

from pipelineiq.auth.tokens import TokenKind, TokenValidationError, decode_token
from pipelineiq.config import get_settings
from pipelineiq.contracts import (
    RepositoryCreate,
    RepositoryResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from pipelineiq.database import database_state
from pipelineiq.errors import PipelineIQError
from pipelineiq.models import (
    AutoFixExecution,
    AutoFixFeedback,
    AutoFixMemory,
    PipelineRun,
    Repository,
    WebhookEvent,
    Workspace,
)
from pipelineiq.services.workspaces import (
    find_owned_workspace,
    repository_response,
    workspace_response,
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


async def require_owner_id(request: Request) -> str:
    settings = get_settings()
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise PipelineIQError(
            status_code=401,
            code="AUTH_REQUIRED",
            message="Authentication is required",
        )
    try:
        claims = decode_token(token, expected_kind=TokenKind.SESSION, settings=settings)
    except TokenValidationError as exc:
        raise PipelineIQError(
            status_code=401,
            code="AUTH_SESSION_INVALID",
            message="Session is invalid or expired",
        ) from exc
    if not database_state.ready:
        raise PipelineIQError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Workspace persistence is temporarily unavailable",
        )
    return claims.sub


async def owned_workspace_or_404(workspace_id: str, owner_id: str) -> Workspace:
    workspace = await find_owned_workspace(workspace_id, owner_id)
    if workspace is None:
        raise PipelineIQError(
            status_code=404,
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
        )
    return workspace


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(request: Request) -> list[WorkspaceResponse]:
    owner_id = await require_owner_id(request)
    owner_object_id = PydanticObjectId(owner_id)
    workspaces = await Workspace.find(Workspace.owner_id == owner_object_id).sort(
        "-created_at"
    ).to_list()
    return [workspace_response(workspace) for workspace in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(request: Request, payload: WorkspaceCreate) -> WorkspaceResponse:
    owner_id = await require_owner_id(request)
    workspace = await Workspace(
        name=payload.name,
        description=payload.description,
        owner_id=PydanticObjectId(owner_id),
        risk_profile=payload.risk_profile,
    ).insert()
    return workspace_response(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(request: Request, workspace_id: str) -> WorkspaceResponse:
    workspace = await owned_workspace_or_404(workspace_id, await require_owner_id(request))
    return workspace_response(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    request: Request, workspace_id: str, payload: WorkspaceUpdate
) -> WorkspaceResponse:
    workspace = await owned_workspace_or_404(workspace_id, await require_owner_id(request))
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(workspace, field, value)
    workspace.updated_at = datetime.now(UTC)
    await workspace.save()
    return workspace_response(workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(request: Request, workspace_id: str) -> dict[str, str]:
    workspace = await owned_workspace_or_404(workspace_id, await require_owner_id(request))
    workspace_id_value = workspace.id
    installation_id = workspace.github_installation_id
    await workspace.delete()
    for model in (
        Repository,
        PipelineRun,
        AutoFixExecution,
        AutoFixFeedback,
        AutoFixMemory,
    ):
        await model.get_motor_collection().delete_many({"workspace_id": workspace_id_value})
    if installation_id is not None:
        await WebhookEvent.get_motor_collection().delete_many(
            {"installation_id": installation_id}
        )
    return {"detail": "Workspace deleted"}


@router.get("/{workspace_id}/repositories", response_model=list[RepositoryResponse])
async def list_repositories(request: Request, workspace_id: str) -> list[RepositoryResponse]:
    workspace = await owned_workspace_or_404(workspace_id, await require_owner_id(request))
    repositories = await Repository.find(Repository.workspace_id == workspace.id).to_list()
    return [repository_response(repository) for repository in repositories]


@router.post(
    "/{workspace_id}/repositories",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_repository(
    request: Request, workspace_id: str, payload: RepositoryCreate
) -> RepositoryResponse:
    workspace = await owned_workspace_or_404(workspace_id, await require_owner_id(request))
    owner_id = PydanticObjectId(str(workspace.owner_id))
    repository = await Repository(
        **payload.model_dump(),
        workspace_id=workspace.id,
        connected_by=owner_id,
    ).insert()
    return repository_response(repository)


@router.delete("/{workspace_id}/repositories/{repo_id}")
async def disconnect_repository(
    request: Request, workspace_id: str, repo_id: str
) -> dict[str, str]:
    workspace = await owned_workspace_or_404(workspace_id, await require_owner_id(request))
    try:
        repository = await Repository.find_one(
            Repository.id == PydanticObjectId(repo_id),
            Repository.workspace_id == workspace.id,
        )
    except ValueError:
        repository = None
    if repository is None:
        raise PipelineIQError(
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
            message="Repository not found",
        )
    await repository.delete()
    return {"detail": "Repository disconnected"}
