import hmac
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse

from pipelineiq.auth.crypto import SecretCipher
from pipelineiq.auth.tokens import (
    TokenKind,
    TokenValidationError,
    create_oauth_state,
    create_session_token,
    decode_token,
)
from pipelineiq.config import Settings, get_settings
from pipelineiq.database import database_state
from pipelineiq.errors import PipelineIQError
from pipelineiq.services.github_oauth import (
    AuthenticatedUser,
    GitHubAuthentication,
    HttpGitHubOAuthProvider,
    MongoAuthUserStore,
    OAuthProviderError,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _require_oauth_config(settings: Settings) -> None:
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise PipelineIQError(
            status_code=503,
            code="AUTH_GITHUB_NOT_CONFIGURED",
            message="GitHub OAuth is not configured",
        )


def _set_private_cookie(
    response: Response,
    *,
    name: str,
    value: str,
    max_age: int,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


@router.get("/github", response_class=RedirectResponse)
async def start_github_oauth() -> RedirectResponse:
    settings = get_settings()
    _require_oauth_config(settings)
    state = create_oauth_state(settings)
    query = urlencode(
        {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": settings.GITHUB_OAUTH_SCOPES,
            "state": state,
        }
    )
    response = RedirectResponse(f"{settings.GITHUB_AUTHORIZE_URL}?{query}", status_code=302)
    _set_private_cookie(
        response,
        name=settings.OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=600,
        settings=settings,
    )
    return response


@router.get("/github/callback", response_class=RedirectResponse)
async def github_oauth_callback(
    request: Request,
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
) -> RedirectResponse:
    settings = get_settings()
    _require_oauth_config(settings)
    error_url = f"{settings.FRONTEND_URL}/?error=oauth_failed"
    piq_oauth_state = request.cookies.get(settings.OAUTH_STATE_COOKIE_NAME)
    if not piq_oauth_state or not hmac.compare_digest(state, piq_oauth_state):
        return RedirectResponse(error_url, status_code=302)
    try:
        decode_token(state, expected_kind=TokenKind.OAUTH_STATE, settings=settings)
    except TokenValidationError:
        return RedirectResponse(error_url, status_code=302)
    if not database_state.ready:
        raise PipelineIQError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Authentication persistence is temporarily unavailable",
        )

    authentication = GitHubAuthentication(
        provider=HttpGitHubOAuthProvider(settings),
        store=MongoAuthUserStore(),
        cipher=SecretCipher(settings),
    )
    try:
        user = await authentication.authenticate(code)
    except OAuthProviderError:
        return RedirectResponse(error_url, status_code=302)

    session = create_session_token(user.id, settings)
    response = RedirectResponse(f"{settings.FRONTEND_URL}/dashboard", status_code=302)
    response.delete_cookie(settings.OAUTH_STATE_COOKIE_NAME, path="/")
    _set_private_cookie(
        response,
        name=settings.SESSION_COOKIE_NAME,
        value=session,
        max_age=settings.SESSION_EXPIRY_DAYS * 86_400,
        settings=settings,
    )
    return response


@router.get("/me", response_model=AuthenticatedUser)
async def current_user(request: Request) -> AuthenticatedUser:
    settings = get_settings()
    session = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session:
        raise PipelineIQError(
            status_code=401,
            code="AUTH_REQUIRED",
            message="Authentication is required",
        )
    try:
        claims = decode_token(session, expected_kind=TokenKind.SESSION, settings=settings)
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
            message="Authentication persistence is temporarily unavailable",
        )
    user = await MongoAuthUserStore().get_user(claims.sub)
    if user is None:
        raise PipelineIQError(
            status_code=401,
            code="AUTH_USER_NOT_FOUND",
            message="Authenticated user no longer exists",
        )
    return user


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    settings = get_settings()
    response.delete_cookie(
        settings.SESSION_COOKIE_NAME,
        path="/",
        domain=settings.COOKIE_DOMAIN,
    )
    return {"detail": "Logged out"}
