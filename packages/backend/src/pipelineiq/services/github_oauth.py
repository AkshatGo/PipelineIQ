from dataclasses import dataclass
from typing import Protocol

import httpx
from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from pipelineiq.auth.crypto import SecretCipher
from pipelineiq.config import Settings
from pipelineiq.models import GitHubOrganization, User, utc_now


class OAuthProviderError(RuntimeError):
    pass


class GitHubUserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class GitHubEmail(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str
    primary: bool = False
    verified: bool = False


class GitHubOrganizationPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    login: str
    avatar_url: str | None = None
    description: str | None = None
    url: str | None = None


class GitHubIdentity(BaseModel):
    github_id: int
    username: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    organizations: list[GitHubOrganization] = Field(default_factory=list)


class AuthenticatedUser(BaseModel):
    id: str
    github_id: int
    username: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    organizations: list[GitHubOrganization]
    last_login: str
    created_at: str


class GitHubOAuthProvider(Protocol):
    async def exchange_code(self, code: str) -> str: ...

    async def fetch_identity(self, access_token: str) -> GitHubIdentity: ...


class AuthUserStore(Protocol):
    async def upsert_identity(
        self, identity: GitHubIdentity, encrypted_access_token: str
    ) -> AuthenticatedUser: ...

    async def get_user(self, user_id: str) -> AuthenticatedUser | None: ...


class HttpGitHubOAuthProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self, token: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "PipelineIQ/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def exchange_code(self, code: str) -> str:
        if not self.settings.GITHUB_CLIENT_ID or not self.settings.GITHUB_CLIENT_SECRET:
            raise OAuthProviderError("GitHub OAuth is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                self.settings.GITHUB_TOKEN_URL,
                headers=self._headers(),
                data={
                    "client_id": self.settings.GITHUB_CLIENT_ID,
                    "client_secret": self.settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": self.settings.GITHUB_REDIRECT_URI,
                },
            )
        if response.is_error:
            raise OAuthProviderError("GitHub rejected the authorization code")
        access_token = response.json().get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise OAuthProviderError("GitHub did not return an access token")
        return access_token

    async def fetch_identity(self, access_token: str) -> GitHubIdentity:
        headers = self._headers(access_token)
        async with httpx.AsyncClient(
            timeout=15, headers=headers, base_url=self.settings.GITHUB_API_URL
        ) as client:
            user_response, orgs_response, emails_response = await _fetch_identity_responses(client)
        profile = GitHubUserProfile.model_validate(user_response.json())
        organizations = [
            GitHubOrganization(**GitHubOrganizationPayload.model_validate(item).model_dump())
            for item in orgs_response.json()
        ]
        email = profile.email
        if not email and not emails_response.is_error:
            emails = [GitHubEmail.model_validate(item) for item in emails_response.json()]
            primary = next((item.email for item in emails if item.primary and item.verified), None)
            email = primary
        return GitHubIdentity(
            github_id=profile.id,
            username=profile.login,
            display_name=profile.name,
            email=email,
            avatar_url=profile.avatar_url,
            organizations=organizations,
        )


async def _fetch_identity_responses(
    client: httpx.AsyncClient,
) -> tuple[httpx.Response, httpx.Response, httpx.Response]:
    user_response = await client.get("/user")
    orgs_response = await client.get("/user/orgs")
    emails_response = await client.get("/user/emails")
    if user_response.is_error or orgs_response.is_error:
        raise OAuthProviderError("Unable to fetch GitHub identity")
    return user_response, orgs_response, emails_response


class MongoAuthUserStore:
    async def upsert_identity(
        self, identity: GitHubIdentity, encrypted_access_token: str
    ) -> AuthenticatedUser:
        user = await User.find_one(User.github_id == identity.github_id)
        now = utc_now()
        if user is None:
            user = User(
                github_id=identity.github_id,
                username=identity.username,
                display_name=identity.display_name,
                email=identity.email,
                avatar_url=identity.avatar_url,
                github_access_token=encrypted_access_token,
                organizations=identity.organizations,
                last_login=now,
            )
            await user.insert()
        else:
            user.username = identity.username
            user.display_name = identity.display_name
            user.email = identity.email
            user.avatar_url = identity.avatar_url
            user.github_access_token = encrypted_access_token
            user.organizations = identity.organizations
            user.last_login = now
            await user.save()
        return _to_authenticated_user(user)

    async def get_user(self, user_id: str) -> AuthenticatedUser | None:
        try:
            object_id = PydanticObjectId(user_id)
        except ValueError:
            return None
        user = await User.get(object_id)
        return _to_authenticated_user(user) if user and user.is_active else None


def _to_authenticated_user(user: User) -> AuthenticatedUser:
    if user.id is None:
        raise ValueError("Persisted user is missing an ID")
    return AuthenticatedUser(
        id=str(user.id),
        github_id=user.github_id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        avatar_url=user.avatar_url,
        organizations=user.organizations,
        last_login=user.last_login.isoformat(),
        created_at=user.created_at.isoformat(),
    )


@dataclass
class GitHubAuthentication:
    provider: GitHubOAuthProvider
    store: AuthUserStore
    cipher: SecretCipher

    async def authenticate(self, code: str) -> AuthenticatedUser:
        access_token = await self.provider.exchange_code(code)
        identity = await self.provider.fetch_identity(access_token)
        return await self.store.upsert_identity(identity, self.cipher.encrypt(access_token))
