from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pipelineiq.auth.crypto import SecretCipher
from pipelineiq.auth.tokens import (
    TokenKind,
    TokenValidationError,
    create_oauth_state,
    create_session_token,
    decode_token,
)
from pipelineiq.config import Settings
from pipelineiq.models import GitHubOrganization
from pipelineiq.services.github_oauth import (
    AuthenticatedUser,
    GitHubAuthentication,
    GitHubIdentity,
)


class FakeProvider:
    async def exchange_code(self, code: str) -> str:
        assert code == "temporary-code"
        return "github-access-token"

    async def fetch_identity(self, access_token: str) -> GitHubIdentity:
        assert access_token == "github-access-token"
        return GitHubIdentity(
            github_id=123,
            username="octocat",
            display_name="The Octocat",
            organizations=[GitHubOrganization(id=1, login="github")],
        )


class FakeUserStore:
    def __init__(self) -> None:
        self.encrypted_access_token: str | None = None

    async def upsert_identity(
        self, identity: GitHubIdentity, encrypted_access_token: str
    ) -> AuthenticatedUser:
        self.encrypted_access_token = encrypted_access_token
        now = datetime.now(UTC).isoformat()
        return AuthenticatedUser(
            id="66f8a1b2c3d4e5f6a7b8c9d0",
            github_id=identity.github_id,
            username=identity.username,
            display_name=identity.display_name,
            organizations=identity.organizations,
            last_login=now,
            created_at=now,
        )

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        del user_id
        return None


def test_session_token_round_trip_and_purpose_check() -> None:
    settings = Settings(JWT_SECRET="a-secure-test-secret-that-is-at-least-32-chars")
    session = create_session_token("user-123", settings)

    claims = decode_token(session, expected_kind=TokenKind.SESSION, settings=settings)

    assert claims.sub == "user-123"
    assert claims.kind is TokenKind.SESSION
    with pytest.raises(TokenValidationError):
        decode_token(session, expected_kind=TokenKind.OAUTH_STATE, settings=settings)


def test_oauth_state_rejects_tampering() -> None:
    settings = Settings(JWT_SECRET="a-secure-test-secret-that-is-at-least-32-chars")
    state = create_oauth_state(settings)

    with pytest.raises(TokenValidationError):
        decode_token(state + "tampered", expected_kind=TokenKind.OAUTH_STATE, settings=settings)


def test_secret_cipher_encrypts_and_decrypts() -> None:
    settings = Settings(JWT_SECRET="a-secure-test-secret-that-is-at-least-32-chars")
    cipher = SecretCipher(settings)

    encrypted = cipher.encrypt("github-token")

    assert encrypted != "github-token"
    assert cipher.decrypt(encrypted) == "github-token"


@pytest.mark.asyncio
async def test_authentication_encrypts_provider_token_before_storage() -> None:
    settings = Settings(JWT_SECRET="a-secure-test-secret-that-is-at-least-32-chars")
    cipher = SecretCipher(settings)
    store = FakeUserStore()
    authentication = GitHubAuthentication(provider=FakeProvider(), store=store, cipher=cipher)

    user = await authentication.authenticate("temporary-code")

    assert user.username == "octocat"
    assert store.encrypted_access_token is not None
    assert store.encrypted_access_token != "github-access-token"
    assert cipher.decrypt(store.encrypted_access_token) == "github-access-token"


def test_production_rejects_development_security_defaults() -> None:
    with pytest.raises(ValidationError, match="Production security settings are missing"):
        Settings(APP_ENV="production")
