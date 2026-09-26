"""Workspace service: collaborative workspace management and legacy workspace functions."""

from __future__ import annotations

import uuid
from typing import Any

from beanie import PydanticObjectId, SortDirection

from pipelineiq.contracts import (
    RepositoryResponse,
    WorkspaceResponse,
)
from pipelineiq.github.github_app_client import GitHubAppClient
from pipelineiq.models import (
    CollaborativeWorkspace,
    DocumentVersion,
    IncidentEvent,
    PipelineRun,
    Repository,
    ValidationRun,
    Workspace,
    WorkspaceDocument,
    utc_now,
)

# Legacy workspace functions (for backward compatibility)


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


# Collaborative workspace functions (new)


async def create_collaborative_workspace(
    pipeline_run: PipelineRun,
    owner_id: PydanticObjectId,
) -> CollaborativeWorkspace:
    """Create a collaborative workspace from a failed pipeline run."""

    collaborative_workspace = CollaborativeWorkspace(
        incident_id=pipeline_run.id,
        workspace_id=str(uuid.uuid4()),
        repository_full_name=pipeline_run.repository_full_name,
        base_branch=pipeline_run.branch or "main",
        head_branch=pipeline_run.branch or "main",
        head_sha=pipeline_run.commit_sha or "",
        owner_id=owner_id,
        participants=[],
        status="initializing",
    )

    await collaborative_workspace.insert()
    return collaborative_workspace


async def get_collaborative_workspace(
    workspace_id: str,
    owner_id: PydanticObjectId,
) -> CollaborativeWorkspace | None:
    """Get a collaborative workspace by ID."""
    return await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.workspace_id == workspace_id,
        CollaborativeWorkspace.owner_id == owner_id,
    )


async def get_collaborative_workspace_by_incident(
    incident_id: PydanticObjectId,
    owner_id: PydanticObjectId,
) -> CollaborativeWorkspace | None:
    """Get a collaborative workspace by incident ID."""
    return await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.incident_id == incident_id,
        CollaborativeWorkspace.owner_id == owner_id,
    )


async def initialize_workspace_documents(
    collaborative_workspace: CollaborativeWorkspace,
    client: GitHubAppClient,
    installation_id: int,
) -> list[WorkspaceDocument]:
    """Initialize workspace documents from the repository at the head commit."""
    if not collaborative_workspace.repository_full_name or not collaborative_workspace.head_sha:
        return []

    owner, repo = collaborative_workspace.repository_full_name.split("/", 1)

    # Get the tree at the head commit
    try:
        commit = await client.get_commit(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            sha=collaborative_workspace.head_sha,
        )
        tree_sha = commit.get("tree", {}).get("sha")
        if not tree_sha:
            return []

        tree = await client.get_tree(installation_id, owner, repo, tree_sha, recursive=True)
        files = tree.get("tree", [])

        documents = []
        for file in files:
            if file.get("type") != "blob":
                continue

            path = file.get("path", "")
            if not path:
                continue

            # Skip binary files and large files
            if file.get("size", 0) > 100_000:  # 100KB limit
                continue

            # Determine language from extension
            language = _detect_language(path)

            # Fetch file content
            content_result = await client.get_file_content(
                installation_id=installation_id,
                owner=owner,
                repo=repo,
                path=path,
                ref=collaborative_workspace.head_sha,
            )

            if not content_result or "content" not in content_result:
                continue

            import base64

            try:
                content = base64.b64decode(content_result["content"]).decode("utf-8")
            except Exception:
                continue

            doc = WorkspaceDocument(
                workspace_id=collaborative_workspace.id,
                path=path,
                language=language,
                content=content,
                original_content=content,
                version=0,
                last_modified_by=collaborative_workspace.owner_id,
                is_binary=False,
            )
            documents.append(doc)

        if documents:
            await WorkspaceDocument.insert_many(documents)

        return documents
    except Exception:
        return []


async def get_workspace_documents(
    workspace_id: PydanticObjectId,
) -> list[WorkspaceDocument]:
    """Get all documents in a collaborative workspace."""
    return await WorkspaceDocument.find(WorkspaceDocument.workspace_id == workspace_id).to_list()


async def update_workspace_document(
    workspace_id: PydanticObjectId,
    path: str,
    content: str,
    author_id: PydanticObjectId,
    yjs_state: bytes | None = None,
) -> WorkspaceDocument | None:
    """Update a workspace document."""
    doc = await WorkspaceDocument.find_one(
        WorkspaceDocument.workspace_id == workspace_id,
        WorkspaceDocument.path == path,
    )

    if not doc:
        return None

    doc.content = content
    doc.version += 1
    doc.last_modified_by = author_id
    doc.last_modified_at = utc_now()
    if yjs_state:
        doc.yjs_state = yjs_state

    await doc.save()
    return doc


async def create_document_version(
    workspace_id: PydanticObjectId,
    document_id: PydanticObjectId,
    author_id: PydanticObjectId,
    author_type: str,
    message: str,
    tags: list[str],
) -> DocumentVersion:
    """Create a new version checkpoint."""
    doc = await WorkspaceDocument.get(document_id)
    if not doc:
        raise ValueError("Document not found")

    # Get the latest version number
    latest_version = (
        await DocumentVersion.find(
            DocumentVersion.workspace_id == workspace_id,
            DocumentVersion.document_id == document_id,
        )
        .sort([("version_number", SortDirection.DESCENDING)])
        .first_or_none()
    )

    version_number = (latest_version.version_number + 1) if latest_version else 1
    parent_version_id = latest_version.id if latest_version else None

    version = DocumentVersion(
        workspace_id=workspace_id,
        document_id=document_id,
        version_number=version_number,
        parent_version_id=parent_version_id,
        content_snapshot=doc.content,
        operations=[],  # Would contain Yjs operations in real implementation
        author_id=author_id,
        author_type=author_type,
        message=message,
        tags=tags,
    )

    await version.insert()
    return version


async def get_document_versions(
    workspace_id: PydanticObjectId,
    document_id: PydanticObjectId,
    limit: int = 50,
) -> list[DocumentVersion]:
    """Get version history for a document."""
    return (
        await DocumentVersion.find(
            DocumentVersion.workspace_id == workspace_id,
            DocumentVersion.document_id == document_id,
        )
        .sort([("version_number", SortDirection.DESCENDING)])
        .limit(limit)
        .to_list()
    )


async def restore_document_version(
    workspace_id: PydanticObjectId,
    version_id: PydanticObjectId,
    author_id: PydanticObjectId,
) -> WorkspaceDocument | None:
    """Restore a document to a previous version."""
    version = await DocumentVersion.get(version_id)
    if not version or version.workspace_id != workspace_id:
        return None

    doc = await WorkspaceDocument.get(version.document_id)
    if not doc or doc.workspace_id != workspace_id or doc.id is None:
        return None

    # Create a new version before restoring
    await create_document_version(
        workspace_id=workspace_id,
        document_id=doc.id,
        author_id=author_id,
        author_type="human",
        message=f"Restored from version {version.version_number}",
        tags=["restore"],
    )

    # Restore content
    doc.content = version.content_snapshot
    doc.version += 1
    doc.last_modified_by = author_id
    doc.last_modified_at = utc_now()
    await doc.save()

    return doc


async def log_incident_event(
    incident_id: PydanticObjectId,
    workspace_id: PydanticObjectId,
    actor_id: PydanticObjectId,
    actor_type: str,
    actor_name: str,
    event_type: str,
    action: str,
    description: str,
    document_id: PydanticObjectId | None = None,
    version_id: PydanticObjectId | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> IncidentEvent:
    """Log an incident event."""
    event = IncidentEvent(
        incident_id=incident_id,
        workspace_id=workspace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        actor_name=actor_name,
        type=event_type,
        action=action,
        description=description,
        document_id=document_id,
        version_id=version_id,
        before=before or {},
        after=after or {},
        metadata=metadata or {},
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    await event.insert()
    return event


async def get_incident_timeline(
    incident_id: PydanticObjectId,
    limit: int = 100,
) -> list[IncidentEvent]:
    """Get incident event timeline."""
    return (
        await IncidentEvent.find(
            IncidentEvent.incident_id == incident_id,
        )
        .sort([("timestamp", SortDirection.ASCENDING)])
        .limit(limit)
        .to_list()
    )


async def start_validation_run(
    workspace_id: PydanticObjectId,
    version_id: PydanticObjectId,
    triggered_by: PydanticObjectId,
) -> ValidationRun:
    """Start a validation run for a workspace version."""
    validation = ValidationRun(
        workspace_id=workspace_id,
        version_id=version_id,
        triggered_by=triggered_by,
        status="pending",
        stages=[],
    )
    await validation.insert()
    return validation


async def update_validation_stage(
    validation_id: PydanticObjectId,
    stage_name: str,
    status: str,
    output: str | None = None,
    error: str | None = None,
) -> None:
    """Update a validation stage result."""
    validation = await ValidationRun.get(validation_id)
    if not validation:
        return

    stage = next((s for s in validation.stages if s["name"] == stage_name), None)
    now = utc_now()

    if stage:
        stage["status"] = status
        if output is not None:
            stage["output"] = output
        if error is not None:
            stage["error"] = error
        if status == "running" and not stage.get("started_at"):
            stage["started_at"] = now
        if status in ("passed", "failed"):
            stage["completed_at"] = now
    else:
        validation.stages.append(
            {
                "name": stage_name,
                "status": status,
                "command": "",
                "output": output,
                "error": error,
                "started_at": now if status == "running" else None,
                "completed_at": now if status in ("passed", "failed") else None,
            }
        )

    if all(s["status"] in ("passed", "failed") for s in validation.stages):
        validation.status = (
            "passed" if all(s["status"] == "passed" for s in validation.stages) else "failed"
        )
        validation.completed_at = now

    validation.updated_at = utc_now()
    await validation.save()


async def get_validation_runs(
    workspace_id: PydanticObjectId,
    limit: int = 20,
) -> list[ValidationRun]:
    """Get validation runs for a workspace."""
    return (
        await ValidationRun.find(
            ValidationRun.workspace_id == workspace_id,
        )
        .sort([("created_at", SortDirection.DESCENDING)])
        .limit(limit)
        .to_list()
    )


def _detect_language(path: str) -> str:
    """Detect programming language from file extension."""
    ext = path.split(".")[-1].lower() if "." in path else ""
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "jsx": "javascript",
        "tsx": "typescript",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "md": "markdown",
        "dockerfile": "dockerfile",
        "sh": "bash",
        "bash": "bash",
        "go": "go",
        "rs": "rust",
        "java": "java",
        "kt": "kotlin",
        "swift": "swift",
        "rb": "ruby",
        "php": "php",
        "cs": "csharp",
        "cpp": "cpp",
        "c": "c",
        "h": "c",
        "hpp": "cpp",
        "sql": "sql",
        "html": "html",
        "css": "css",
        "scss": "scss",
        "less": "less",
        "xml": "xml",
        "toml": "toml",
        "ini": "ini",
        "cfg": "ini",
        "conf": "ini",
    }
    return language_map.get(ext, "text")
