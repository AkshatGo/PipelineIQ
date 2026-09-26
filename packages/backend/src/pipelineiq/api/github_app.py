"""GitHub App installation and management endpoints."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from pipelineiq.auth.tokens import TokenKind, TokenValidationError, decode_token
from pipelineiq.config import get_settings
from pipelineiq.contracts import WebhookEventResponse
from pipelineiq.database import database_state
from pipelineiq.errors import PipelineIQError
from pipelineiq.models import WebhookEvent, Workspace
from pipelineiq.services.github_app import (
    GitHubAppError,
    GitHubAppInstallation,
    parse_installation_state,
)
from pipelineiq.services.workspaces import find_owned_workspace

router = APIRouter(prefix="/api/workspaces", tags=["github-app"])


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


@router.get("/{workspace_id}/github/install", response_class=RedirectResponse)
async def initiate_github_app_installation(
    request: Request, workspace_id: str
) -> RedirectResponse:
    """Initiate GitHub App installation flow for a workspace."""
    settings = get_settings()
    if not (
        settings.GITHUB_APP_ID
        or settings.GITHUB_APP_SLUG
        or settings.GITHUB_APP_PRIVATE_KEY
    ):
        raise PipelineIQError(
            status_code=503,
            code="GITHUB_APP_NOT_CONFIGURED",
            message="GitHub App is not configured",
        )

    owner_id = await require_owner_id(request)
    workspace = await owned_workspace_or_404(workspace_id, owner_id)

    from pipelineiq.auth.crypto import SecretCipher

    installation = GitHubAppInstallation(settings, SecretCipher(settings))
    install_url = await installation.initiate_installation(str(workspace.id), owner_id)
    return RedirectResponse(install_url, status_code=302)


@router.delete("/{workspace_id}/github/installation")
async def disconnect_github_app_installation(
    request: Request, workspace_id: str
) -> dict[str, str]:
    """Disconnect GitHub App installation from workspace."""
    settings = get_settings()
    if not settings.GITHUB_APP_ID:
        raise PipelineIQError(
            status_code=503,
            code="GITHUB_APP_NOT_CONFIGURED",
            message="GitHub App is not configured",
        )

    owner_id = await require_owner_id(request)
    workspace = await owned_workspace_or_404(workspace_id, owner_id)

    if not workspace.github_installation_id:
        raise PipelineIQError(
            status_code=404,
            code="GITHUB_APP_NOT_INSTALLED",
            message="No GitHub App installation connected to this workspace",
        )

    from pipelineiq.auth.crypto import SecretCipher

    installation = GitHubAppInstallation(settings, SecretCipher(settings))
    await installation.disconnect_installation(workspace)
    return {"detail": "GitHub App disconnected"}


@router.get("/{workspace_id}/github/events", response_model=list[WebhookEventResponse])
async def list_webhook_events(
    request: Request, workspace_id: str, limit: int = Query(default=10, ge=1, le=50)
) -> list[WebhookEventResponse]:
    """List recent webhook events for a workspace."""
    owner_id = await require_owner_id(request)
    workspace = await owned_workspace_or_404(workspace_id, owner_id)

    if not workspace.github_installation_id:
        return []

    events = await WebhookEvent.find(
        WebhookEvent.installation_id == workspace.github_installation_id
    ).sort("-received_at").limit(limit).to_list()

    return [
        WebhookEventResponse(
            delivery_id=event.delivery_id,
            event_type=event.event_type,
            action=event.action,
            repository_full_name=event.repository_full_name,
            received_at=event.received_at.isoformat(),
        )
        for event in events
    ]


# GitHub App installation callback (no workspace prefix, called by GitHub)
github_app_callback_router = APIRouter(tags=["github-app-callback"])


@github_app_callback_router.get(
    "/api/github/installations/callback", response_class=RedirectResponse
)
async def github_app_installation_callback(
    request: Request,
    installation_id: int = Query(..., ge=1),
    setup_action: str | None = Query(default=None),
    state: str = Query(..., min_length=1),
) -> RedirectResponse:
    """Handle GitHub App installation callback."""
    settings = get_settings()
    if not (
        settings.GITHUB_APP_ID
        or settings.GITHUB_APP_SLUG
        or settings.GITHUB_APP_PRIVATE_KEY
    ):
        error_url = f"{settings.FRONTEND_URL}/?installation=github_not_configured"
        return RedirectResponse(error_url, status_code=302)

    if not database_state.ready:
        error_url = f"{settings.FRONTEND_URL}/?installation=db_unavailable"
        return RedirectResponse(error_url, status_code=302)

    try:
        workspace_id, user_id = parse_installation_state(state, settings)
    except TokenValidationError:
        error_url = f"{settings.FRONTEND_URL}/?installation=invalid_state"
        return RedirectResponse(error_url, status_code=302)

    workspace = await Workspace.get(workspace_id)
    if not workspace:
        error_url = f"{settings.FRONTEND_URL}/?installation=workspace_missing"
        return RedirectResponse(error_url, status_code=302)

    if str(workspace.owner_id) != user_id:
        error_url = f"{settings.FRONTEND_URL}/?installation=ownership_mismatch"
        return RedirectResponse(error_url, status_code=302)

    from pipelineiq.auth.crypto import SecretCipher

    installation = GitHubAppInstallation(settings, SecretCipher(settings))
    try:
        await installation.handle_callback(installation_id, state, setup_action)
    except GitHubAppError:
        error_url = f"{settings.FRONTEND_URL}/?installation=github_lookup_failed"
        return RedirectResponse(error_url, status_code=302)

    success_url = f"{settings.FRONTEND_URL}/workspace/{workspace_id}?installation=success"
    return RedirectResponse(success_url, status_code=302)