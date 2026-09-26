"""Collaborative workspace API endpoints."""

from typing import Any

from beanie import PydanticObjectId, SortDirection
from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect, status

from pipelineiq.auth.tokens import TokenKind, TokenValidationError, decode_token
from pipelineiq.config import get_settings
from pipelineiq.contracts import (
    CollaborativeWorkspaceCreate,
    CollaborativeWorkspaceResponse,
    CreateCheckpointRequest,
    DocumentVersionResponse,
    IncidentEventResponse,
    RestoreVersionRequest,
    ValidationRunResponse,
    WorkspaceDocumentResponse,
    WorkspaceParticipantResponse,
)
from pipelineiq.database import database_state
from pipelineiq.errors import PipelineIQError
from pipelineiq.github.github_app_client import GitHubAppClient
from pipelineiq.models import (
    CollaborativeWorkspace,
    DocumentVersion,
    IncidentEvent,
    PipelineRun,
    ValidationRun,
    Workspace,
    WorkspaceDocument,
)
from pipelineiq.services.workspaces import (
    create_collaborative_workspace,
    create_document_version,
    get_document_versions,
    get_validation_runs,
    initialize_workspace_documents,
    restore_document_version,
    start_validation_run,
    update_workspace_document,
)


class ConnectionManager:
    """Manages WebSocket connections for collaborative workspaces."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, workspace_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)

    def disconnect(self, workspace_id: str, websocket: WebSocket) -> None:
        if workspace_id in self.active_connections:
            self.active_connections[workspace_id].remove(websocket)
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]

    async def broadcast(
        self, workspace_id: str, message: dict[str, Any], exclude: WebSocket | None = None
    ) -> None:
        if workspace_id in self.active_connections:
            for connection in self.active_connections[workspace_id]:
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass


manager = ConnectionManager()


router = APIRouter(prefix="/api/collaborative", tags=["collaborative"])


async def require_owner_id(request: Request) -> PydanticObjectId:
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
    return PydanticObjectId(claims.sub)


async def get_workspace_or_404(
    workspace_id: str, owner_id: PydanticObjectId
) -> CollaborativeWorkspace:
    workspace = await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.workspace_id == workspace_id,
        CollaborativeWorkspace.owner_id == owner_id,
    )
    if not workspace:
        raise PipelineIQError(
            status_code=404,
            code="WORKSPACE_NOT_FOUND",
            message="Collaborative workspace not found",
        )
    assert workspace.id is not None, "Workspace ID must not be None"
    return workspace


async def get_workspace_for_websocket(workspace_id: str) -> CollaborativeWorkspace | None:
    """Get workspace without owner check for WebSocket (auth done via token)."""
    return await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.workspace_id == workspace_id,
    )


@router.post("", response_model=CollaborativeWorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: Request,
    payload: CollaborativeWorkspaceCreate,
) -> CollaborativeWorkspaceResponse:
    """Create a collaborative workspace from a pipeline run."""
    owner_id = await require_owner_id(request)

    pipeline_run = await PipelineRun.get(PydanticObjectId(payload.incident_id))
    if not pipeline_run:
        raise PipelineIQError(
            status_code=404,
            code="PIPELINE_RUN_NOT_FOUND",
            message="Pipeline run not found",
        )

    # Check ownership
    if str(pipeline_run.workspace_id) != str(owner_id):
        workspace = await Workspace.get(pipeline_run.workspace_id)
        if not workspace or str(workspace.owner_id) != str(owner_id):
            raise PipelineIQError(
                status_code=403,
                code="FORBIDDEN",
                message="Not authorized to create workspace for this pipeline run",
            )

    # Check if workspace already exists for this incident
    existing = await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.incident_id == pipeline_run.id,
        CollaborativeWorkspace.owner_id == owner_id,
    )
    if existing:
        return _to_workspace_response(existing)

    owner_object_id = PydanticObjectId(owner_id)
    collaborative_workspace = await create_collaborative_workspace(pipeline_run, owner_object_id)

    # Initialize documents from GitHub
    if pipeline_run.github_installation_id:
        settings = get_settings()
        client = GitHubAppClient(settings)
        await initialize_workspace_documents(
            collaborative_workspace, client, pipeline_run.github_installation_id
        )

    collaborative_workspace.status = "active"
    await collaborative_workspace.save()

    return _to_workspace_response(collaborative_workspace)


@router.get("/{workspace_id}", response_model=CollaborativeWorkspaceResponse)
async def get_workspace(
    request: Request,
    workspace_id: str,
) -> CollaborativeWorkspaceResponse:
    """Get a collaborative workspace."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)
    return _to_workspace_response(workspace)


@router.get("/incident/{incident_id}", response_model=CollaborativeWorkspaceResponse)
async def get_workspace_by_incident(
    request: Request,
    incident_id: str,
) -> CollaborativeWorkspaceResponse:
    """Get a collaborative workspace by incident ID."""
    owner_id = await require_owner_id(request)
    workspace = await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.incident_id == PydanticObjectId(incident_id),
        CollaborativeWorkspace.owner_id == PydanticObjectId(owner_id),
    )
    if not workspace:
        raise PipelineIQError(
            status_code=404,
            code="WORKSPACE_NOT_FOUND",
            message="Collaborative workspace not found",
        )
    return _to_workspace_response(workspace)


@router.get("/{workspace_id}/documents", response_model=list[WorkspaceDocumentResponse])
async def list_documents(
    request: Request,
    workspace_id: str,
) -> list[WorkspaceDocumentResponse]:
    """List all documents in a collaborative workspace."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    documents = await WorkspaceDocument.find(
        WorkspaceDocument.workspace_id == workspace.id
    ).to_list()

    return [_to_document_response(doc) for doc in documents]


@router.patch("/{workspace_id}/documents/{path:path}", response_model=WorkspaceDocumentResponse)
async def update_document(
    request: Request,
    workspace_id: str,
    path: str,
    payload: dict[str, Any],
) -> WorkspaceDocumentResponse:
    """Update a document in the collaborative workspace."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    content = payload.get("content")
    if content is None:
        raise PipelineIQError(
            status_code=400,
            code="INVALID_PAYLOAD",
            message="Content is required",
        )

    yjs_state = payload.get("yjs_state")
    yjs_bytes = None
    if yjs_state:
        import base64

        yjs_bytes = base64.b64decode(yjs_state)

    owner_object_id = PydanticObjectId(owner_id)
    workspace_id_obj = workspace.id
    assert workspace_id_obj is not None
    doc = await update_workspace_document(
        workspace_id=workspace_id_obj,
        path=path,
        content=content,
        author_id=owner_object_id,
        yjs_state=yjs_bytes,
    )

    if not doc:
        raise PipelineIQError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="Document not found",
        )

    return _to_document_response(doc)


@router.post(
    "/{workspace_id}/documents/{path:path}/checkpoint", response_model=DocumentVersionResponse
)
async def create_checkpoint(
    request: Request,
    workspace_id: str,
    path: str,
    payload: CreateCheckpointRequest,
) -> DocumentVersionResponse:
    """Create a version checkpoint for a document."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    doc = await WorkspaceDocument.find_one(
        WorkspaceDocument.workspace_id == workspace.id,
        WorkspaceDocument.path == path,
    )
    if not doc:
        raise PipelineIQError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="Document not found",
        )

    assert doc.id is not None
    workspace_id_obj = workspace.id
    assert workspace_id_obj is not None
    owner_object_id = PydanticObjectId(owner_id)
    version = await create_document_version(
        workspace_id=workspace_id_obj,
        document_id=doc.id,
        author_id=owner_object_id,
        author_type="human",
        message=payload.message,
        tags=payload.tags,
    )

    return _to_version_response(version)


@router.get(
    "/{workspace_id}/documents/{path:path}/versions", response_model=list[DocumentVersionResponse]
)
async def list_versions(
    request: Request,
    workspace_id: str,
    path: str,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[DocumentVersionResponse]:
    """Get version history for a document."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    doc = await WorkspaceDocument.find_one(
        WorkspaceDocument.workspace_id == workspace.id,
        WorkspaceDocument.path == path,
    )
    if not doc:
        raise PipelineIQError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="Document not found",
        )

    assert doc.id is not None
    workspace_id_obj = workspace.id
    assert workspace_id_obj is not None
    versions = await get_document_versions(workspace_id_obj, doc.id, limit=limit)
    return [_to_version_response(v) for v in versions]


@router.post(
    "/{workspace_id}/documents/{path:path}/restore", response_model=WorkspaceDocumentResponse
)
async def restore_version(
    request: Request,
    workspace_id: str,
    path: str,
    payload: RestoreVersionRequest,
) -> WorkspaceDocumentResponse:
    """Restore a document to a previous version."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    doc = await WorkspaceDocument.find_one(
        WorkspaceDocument.workspace_id == workspace.id,
        WorkspaceDocument.path == path,
    )
    if not doc:
        raise PipelineIQError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="Document not found",
        )

    workspace_id_obj = workspace.id
    assert workspace_id_obj is not None
    owner_object_id = PydanticObjectId(owner_id)
    restored_doc = await restore_document_version(
        workspace_id=workspace_id_obj,
        version_id=PydanticObjectId(payload.version_id),
        author_id=owner_object_id,
    )

    if not restored_doc:
        raise PipelineIQError(
            status_code=404,
            code="VERSION_NOT_FOUND",
            message="Version not found or cannot be restored",
        )

    return _to_document_response(restored_doc)


@router.get("/{workspace_id}/timeline", response_model=list[IncidentEventResponse])
async def get_timeline(
    request: Request,
    workspace_id: str,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[IncidentEventResponse]:
    """Get the incident event timeline."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    events = (
        await IncidentEvent.find(
            IncidentEvent.workspace_id == workspace.id,
        )
        .sort([("timestamp", SortDirection.DESCENDING)])
        .limit(limit)
        .to_list()
    )

    return [_to_event_response(e) for e in events]


@router.post(
    "/{workspace_id}/validate",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_validation(
    request: Request,
    workspace_id: str,
    payload: dict[str, str],
) -> ValidationRunResponse:
    """Start a validation run for the current workspace state."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    version_id_str = payload.get("version_id")
    if not version_id_str:
        # Get latest checkpoint
        docs = await WorkspaceDocument.find(
            WorkspaceDocument.workspace_id == workspace.id
        ).to_list()
        if not docs:
            raise PipelineIQError(
                status_code=400,
                code="NO_DOCUMENTS",
                message="No documents to validate",
            )
        latest_version = (
            await DocumentVersion.find(
                DocumentVersion.workspace_id == workspace.id,
                DocumentVersion.document_id == docs[0].id,
            )
            .sort([("version_number", SortDirection.DESCENDING)])
            .first_or_none()
        )
        if not latest_version:
            raise PipelineIQError(
                status_code=400,
                code="NO_VERSIONS",
                message="No version checkpoints to validate",
            )
        assert latest_version.id is not None
        version_id = latest_version.id
    else:
        version_id = PydanticObjectId(version_id_str)

    workspace_id_obj = workspace.id
    assert workspace_id_obj is not None
    owner_object_id = PydanticObjectId(owner_id)
    validation = await start_validation_run(workspace_id_obj, version_id, owner_object_id)

    return _to_validation_response(validation)


@router.get("/{workspace_id}/validations", response_model=list[ValidationRunResponse])
async def list_validations(
    request: Request,
    workspace_id: str,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[ValidationRunResponse]:
    """Get validation runs for a workspace."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    validations = await get_validation_runs(workspace.id, limit=limit)  # type: ignore[arg-type]
    return [_to_validation_response(v) for v in validations]


@router.get("/{workspace_id}/sync-status")
async def get_sync_status(
    request: Request,
    workspace_id: str,
) -> dict[str, Any]:
    """Get the sync status for a collaborative workspace."""
    owner_id = await require_owner_id(request)
    workspace = await get_workspace_or_404(workspace_id, owner_id)

    return {
        "status": "online" if workspace.last_synced_at else "offline",
        "last_synced_at": workspace.last_synced_at.isoformat()
        if workspace.last_synced_at
        else None,
        "workspace_id": workspace.workspace_id,
        "participants": len(workspace.participants),
    }


@router.websocket("/{workspace_id}/ws")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str) -> None:
    """WebSocket endpoint for real-time collaborative editing."""
    # Authenticate via query parameter token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    settings = get_settings()
    try:
        claims = decode_token(token, expected_kind=TokenKind.SESSION, settings=settings)
    except TokenValidationError:
        await websocket.close(code=4001, reason="Invalid session")
        return

    owner_id = PydanticObjectId(claims.sub)
    workspace = await get_workspace_for_websocket(workspace_id)
    if not workspace:
        await websocket.close(code=4004, reason="Workspace not found")
        return

    # Verify ownership or participation
    is_participant = False
    if str(workspace.owner_id) == str(owner_id):
        is_participant = True
    else:
        for p in workspace.participants:
            if str(p.user_id) == str(owner_id):
                is_participant = True
                break

    if not is_participant:
        await websocket.close(code=4003, reason="Not a participant")
        return

    await manager.connect(workspace_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "sync":
                # Broadcast sync message to other participants
                await manager.broadcast(workspace_id, data, exclude=websocket)

            elif message_type == "awareness":
                # Broadcast awareness (cursor, selection) to other participants
                await manager.broadcast(workspace_id, data, exclude=websocket)

            elif message_type == "checkpoint":
                # Create a version checkpoint
                path = data.get("path")
                message = data.get("message", "Checkpoint")
                tags = data.get("tags", [])

                doc = await WorkspaceDocument.find_one(
                    WorkspaceDocument.workspace_id == workspace.id,
                    WorkspaceDocument.path == path,
                )
                if doc:
                    assert doc.id is not None
                    workspace_id_obj = workspace.id
                    assert workspace_id_obj is not None
                    owner_object_id = PydanticObjectId(owner_id)
                    version = await create_document_version(
                        workspace_id=workspace_id_obj,
                        document_id=doc.id,
                        author_id=owner_object_id,
                        author_type="human",
                        message=message,
                        tags=tags,
                    )
                    # Broadcast checkpoint created
                    await manager.broadcast(
                        workspace_id,
                        {
                            "type": "checkpoint_created",
                            "path": path,
                            "version": _to_version_response(version),
                        },
                        exclude=websocket,
                    )

            elif message_type == "presence":
                # Update participant presence
                pass  # Would update participant presence in workspace

    except WebSocketDisconnect:
        manager.disconnect(workspace_id, websocket)
    except Exception as e:
        manager.disconnect(workspace_id, websocket)
        try:
            await websocket.close(code=4000, reason=str(e))
        except Exception:
            pass


def _to_workspace_response(ws: CollaborativeWorkspace) -> CollaborativeWorkspaceResponse:
    return CollaborativeWorkspaceResponse(
        id=str(ws.id),
        incident_id=str(ws.incident_id),
        workspace_id=ws.workspace_id,
        repository_full_name=ws.repository_full_name,
        base_branch=ws.base_branch,
        head_branch=ws.head_branch,
        head_sha=ws.head_sha,
        owner_id=str(ws.owner_id),
        participants=[
            WorkspaceParticipantResponse(
                user_id=str(p.user_id),
                role=p.role,
                joined_at=p.joined_at.isoformat(),
                last_active_at=p.last_active_at.isoformat(),
                presence=p.presence,
            )
            for p in ws.participants
        ],
        status=ws.status,
        created_at=ws.created_at.isoformat(),
        updated_at=ws.updated_at.isoformat(),
        last_synced_at=ws.last_synced_at.isoformat() if ws.last_synced_at else None,
    )


def _to_document_response(doc: WorkspaceDocument) -> WorkspaceDocumentResponse:
    return WorkspaceDocumentResponse(
        id=str(doc.id),
        workspace_id=str(doc.workspace_id),
        path=doc.path,
        language=doc.language,
        content=doc.content,
        original_content=doc.original_content,
        version=doc.version,
        last_modified_by=str(doc.last_modified_by),
        last_modified_at=doc.last_modified_at.isoformat(),
        is_binary=doc.is_binary,
    )


def _to_version_response(v: DocumentVersion) -> DocumentVersionResponse:
    return DocumentVersionResponse(
        id=str(v.id),
        workspace_id=str(v.workspace_id),
        document_id=str(v.document_id),
        version_number=v.version_number,
        parent_version_id=str(v.parent_version_id) if v.parent_version_id else None,
        content_snapshot=v.content_snapshot,
        operations=v.operations,
        author_id=str(v.author_id),
        author_type=v.author_type,
        message=v.message,
        tags=v.tags,
        ci_run_id=str(v.ci_run_id) if v.ci_run_id else None,
        ci_status=v.ci_status,
        ci_url=v.ci_url,
        created_at=v.created_at.isoformat(),
    )


def _to_event_response(e: IncidentEvent) -> IncidentEventResponse:
    return IncidentEventResponse(
        id=str(e.id),
        incident_id=str(e.incident_id),
        workspace_id=str(e.workspace_id),
        actor_id=str(e.actor_id),
        actor_type=e.actor_type,
        actor_name=e.actor_name,
        type=e.type,
        action=e.action,
        description=e.description,
        document_id=str(e.document_id) if e.document_id else None,
        version_id=str(e.version_id) if e.version_id else None,
        before=e.before,
        after=e.after,
        metadata=e.metadata,
        correlation_id=e.correlation_id,
        causation_id=e.causation_id,
        timestamp=e.timestamp.isoformat(),
    )


def _to_validation_response(v: ValidationRun) -> ValidationRunResponse:
    return ValidationRunResponse(
        id=str(v.id),
        workspace_id=str(v.workspace_id),
        version_id=str(v.version_id),
        triggered_by=str(v.triggered_by),
        status=v.status,
        stages=v.stages,
        started_at=v.started_at.isoformat() if v.started_at else None,
        completed_at=v.completed_at.isoformat() if v.completed_at else None,
        logs=v.logs,
        created_at=v.created_at.isoformat(),
    )
