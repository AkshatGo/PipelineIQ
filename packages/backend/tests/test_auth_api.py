from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from pipelineiq.auth.tokens import TokenKind, create_oauth_state, create_session_token, decode_token
from pipelineiq.config import get_settings
from pipelineiq.database import database_state
from pipelineiq.main import app
from pipelineiq.services.github_oauth import (
    AuthenticatedUser,
    GitHubAuthentication,
    MongoAuthUserStore,
)


@pytest.mark.asyncio
async def test_oauth_start_requires_configuration() -> None:
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/auth/github")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_GITHUB_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_oauth_start_sets_signed_state_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    get_settings.cache_clear()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/auth/github")
        settings = get_settings()
        query = parse_qs(urlparse(response.headers["location"]).query)
        state = query["state"][0]
        claims = decode_token(state, expected_kind=TokenKind.OAUTH_STATE, settings=settings)
    finally:
        get_settings.cache_clear()

    assert response.status_code == 302
    assert claims.sub
    assert "piq_oauth_state=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_current_user_requires_session() -> None:
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_logout_expires_session_cookie() -> None:
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"detail": "Logged out"}
    assert "piq_session=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_callback_rejects_mismatched_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    get_settings.cache_clear()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"piq_oauth_state": "cookie-state"},
        ) as client:
            response = await client.get(
                "/api/auth/github/callback",
                params={"code": "code", "state": "sent-state"},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 302
    assert response.headers["location"].endswith("/?error=oauth_failed")


@pytest.mark.asyncio
async def test_callback_issues_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(database_state, "ready", True)
    get_settings.cache_clear()
    settings = get_settings()
    state = create_oauth_state(settings)
    user = AuthenticatedUser(
        id="66f8a1b2c3d4e5f6a7b8c9d0",
        github_id=123,
        username="octocat",
        organizations=[],
        last_login="2026-09-26T00:00:00+00:00",
        created_at="2026-09-26T00:00:00+00:00",
    )

    async def authenticate(self: GitHubAuthentication, code: str) -> AuthenticatedUser:
        del self
        assert code == "valid-code"
        return user

    monkeypatch.setattr(GitHubAuthentication, "authenticate", authenticate)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"piq_oauth_state": state},
        ) as client:
            response = await client.get(
                "/api/auth/github/callback",
                params={"code": "valid-code", "state": state},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 302
    assert response.headers["location"].endswith("/dashboard")
    assert "piq_session=" in response.headers.get_list("set-cookie")[1]
    assert "HttpOnly" in response.headers.get_list("set-cookie")[1]


@pytest.mark.asyncio
async def test_current_user_returns_persisted_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    settings = get_settings()
    user_id = "66f8a1b2c3d4e5f6a7b8c9d0"
    session = create_session_token(user_id, settings)
    user = AuthenticatedUser(
        id=user_id,
        github_id=123,
        username="octocat",
        organizations=[],
        last_login="2026-09-26T00:00:00+00:00",
        created_at="2026-09-26T00:00:00+00:00",
    )

    async def get_user(self: MongoAuthUserStore, requested_id: str) -> AuthenticatedUser:
        del self
        assert requested_id == user_id
        return user

    monkeypatch.setattr(database_state, "ready", True)
    monkeypatch.setattr(MongoAuthUserStore, "get_user", get_user)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={settings.SESSION_COOKIE_NAME: session},
    ) as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "octocat"
