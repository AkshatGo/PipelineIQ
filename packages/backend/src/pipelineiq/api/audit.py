"""Audit log API endpoints."""

from beanie import PydanticObjectId, SortDirection
from fastapi import APIRouter, Query, Request

from pipelineiq.auth.tokens import TokenKind, TokenValidationError, decode_token
from pipelineiq.config import get_settings
from pipelineiq.contracts import (
    AuditEventSummary,
    IncidentEventResponse,
)
from pipelineiq.database import database_state
from pipelineiq.errors import PipelineIQError
from pipelineiq.models import IncidentEvent

router = APIRouter(prefix="/api/audit", tags=["audit"])


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


@router.get("/incident/{incident_id}", response_model=list[IncidentEventResponse])
async def get_incident_timeline(
    request: Request,
    incident_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    actor_type: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
) -> list[IncidentEventResponse]:
    """Get the incident event timeline with optional filtering."""
    owner_id = await require_owner_id(request)

    # Verify the incident belongs to the user (via workspace)
    from pipelineiq.models import PipelineRun

    pipeline_run = await PipelineRun.get(PydanticObjectId(incident_id))
    if not pipeline_run:
        raise PipelineIQError(
            status_code=404,
            code="INCIDENT_NOT_FOUND",
            message="Incident not found",
        )

    # Check ownership
    if str(pipeline_run.workspace_id) != str(owner_id):
        raise PipelineIQError(
            status_code=403,
            code="FORBIDDEN",
            message="Not authorized to access this incident",
        )

    query = IncidentEvent.find(IncidentEvent.incident_id == PydanticObjectId(incident_id))

    if actor_type:
        query = query.find(IncidentEvent.actor_type == actor_type)
    if event_type:
        query = query.find(IncidentEvent.type == event_type)

    events = await query.sort([("timestamp", SortDirection.DESCENDING)]).limit(limit).to_list()
    return [_to_event_response(e) for e in events]


@router.get("/workspace/{workspace_id}", response_model=list[IncidentEventResponse])
async def get_workspace_events(
    request: Request,
    workspace_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    actor_type: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    from_timestamp: str | None = Query(default=None),
    to_timestamp: str | None = Query(default=None),
) -> list[IncidentEventResponse]:
    """Get audit events for a workspace with filtering."""
    from pipelineiq.models import CollaborativeWorkspace

    owner_id = await require_owner_id(request)

    workspace = await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.workspace_id == workspace_id,
        CollaborativeWorkspace.owner_id == PydanticObjectId(owner_id),
    )
    if not workspace:
        raise PipelineIQError(
            status_code=404,
            code="WORKSPACE_NOT_FOUND",
            message="Collaborative workspace not found",
        )

    query = IncidentEvent.find(IncidentEvent.workspace_id == workspace.id)

    if actor_type:
        query = query.find(IncidentEvent.actor_type == actor_type)
    if event_type:
        query = query.find(IncidentEvent.type == event_type)
    if from_timestamp:
        from datetime import datetime
        from_dt = datetime.fromisoformat(from_timestamp.replace("Z", "+00:00"))
        query = query.find(IncidentEvent.timestamp >= from_dt)
    if to_timestamp:
        from datetime import datetime
        to_dt = datetime.fromisoformat(to_timestamp.replace("Z", "+00:00"))
        query = query.find(IncidentEvent.timestamp <= to_dt)

    events = await query.sort([("timestamp", SortDirection.DESCENDING)]).limit(limit).to_list()
    return [_to_event_response(e) for e in events]


@router.get("/workspace/{workspace_id}/summary", response_model=AuditEventSummary)
async def get_workspace_event_summary(
    request: Request,
    workspace_id: str,
) -> AuditEventSummary:
    """Get a summary of audit events for a workspace."""
    from pipelineiq.models import CollaborativeWorkspace

    owner_id = await require_owner_id(request)

    workspace = await CollaborativeWorkspace.find_one(
        CollaborativeWorkspace.workspace_id == workspace_id,
        CollaborativeWorkspace.owner_id == PydanticObjectId(owner_id),
    )
    if not workspace:
        raise PipelineIQError(
            status_code=404,
            code="WORKSPACE_NOT_FOUND",
            message="Collaborative workspace not found",
        )

    events = await IncidentEvent.find(IncidentEvent.workspace_id == workspace.id).to_list()

    actor_type_breakdown: dict[str, int] = {}
    event_type_breakdown: dict[str, int] = {}

    for event in events:
        actor_type_breakdown[event.actor_type] = actor_type_breakdown.get(event.actor_type, 0) + 1
        event_type_breakdown[event.type] = event_type_breakdown.get(event.type, 0) + 1

    timestamps = [e.timestamp for e in events]
    return AuditEventSummary(
        total_events=len(events),
        actor_type_breakdown=actor_type_breakdown,
        event_type_breakdown=event_type_breakdown,
        time_range={
            "earliest": min(timestamps).isoformat() if timestamps else None,
            "latest": max(timestamps).isoformat() if timestamps else None,
        },
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