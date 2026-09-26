from typing import Any

from beanie import PydanticObjectId

from pipelineiq.contracts import RepositoryResponse, WorkspaceResponse
from pipelineiq.models import Repository, Workspace


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def workspace_response(workspace: Workspace) -> WorkspaceResponse:
    if workspace.id is None:
        raise ValueError("Workspace is missing an ID")
    return WorkspaceResponse(
        id=str(workspace.id),
        name=workspace.name,
        description=workspace.description,
        owner_id=str(workspace.owner_id),
        github_installation_id=workspace.github_installation_id,
        github_repository_id=workspace.github_repository_id,
        github_repo_full_name=workspace.github_repo_full_name,
        github_default_branch=workspace.github_default_branch,
        github_repo_private=workspace.github_repo_private,
        github_repo_html_url=workspace.github_repo_html_url,
        github_account_login=workspace.github_account_login,
        github_account_type=workspace.github_account_type,
        slack_devops_mention=workspace.slack_devops_mention,
        risk_profile=workspace.risk_profile,
        connected_at=_iso(workspace.connected_at),
        last_webhook_event_at=_iso(workspace.last_webhook_event_at),
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat(),
        connected=workspace.github_installation_id is not None,
    )


def repository_response(repository: Repository) -> RepositoryResponse:
    if repository.id is None:
        raise ValueError("Repository is missing an ID")
    return RepositoryResponse(
        id=str(repository.id),
        github_repo_id=repository.github_repo_id,
        full_name=repository.full_name,
        name=repository.name,
        private=repository.private,
        html_url=repository.html_url,
        default_branch=repository.default_branch,
        workspace_id=str(repository.workspace_id),
        connected_at=repository.connected_at.isoformat(),
        connected_by=str(repository.connected_by),
    )


async def find_owned_workspace(workspace_id: str, owner_id: str) -> Workspace | None:
    try:
        workspace_object_id = PydanticObjectId(workspace_id)
        owner_object_id = PydanticObjectId(owner_id)
    except ValueError:
        return None
    return await Workspace.find_one(
        Workspace.id == workspace_object_id,
        Workspace.owner_id == owner_object_id,
    )

