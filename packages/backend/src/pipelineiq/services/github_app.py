"""GitHub App integration: installation tokens, API client, webhook handling."""

import json
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt as pyjwt
from beanie import PydanticObjectId
from cryptography.hazmat.primitives import serialization

from pipelineiq.auth.crypto import SecretCipher
from pipelineiq.auth.tokens import TokenKind, create_token, decode_token
from pipelineiq.config import Settings
from pipelineiq.models import Workspace, utc_now


class GitHubAppError(RuntimeError):
    pass


class InstallationTokenCache:
    """In-memory cache for GitHub App installation tokens with TTL."""

    def __init__(self) -> None:
        self._cache: dict[int, tuple[str, float]] = {}

    def get(self, installation_id: int) -> str | None:
        if installation_id in self._cache:
            token, expires_at = self._cache[installation_id]
            if time.time() < expires_at - 60:  # 60s buffer
                return token
            del self._cache[installation_id]
        return None

    def set(self, installation_id: int, token: str, expires_at: float) -> None:
        self._cache[installation_id] = (token, expires_at)


installation_token_cache = InstallationTokenCache()


def generate_jwt(app_id: str, private_key_pem: str) -> str:
    """Generate a GitHub App JWT for authentication."""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": app_id,
    }
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    return pyjwt.encode(payload, private_key, algorithm="RS256")  # type: ignore[arg-type]


async def get_installation_token(
    installation_id: int,
    settings: Settings,
) -> str:
    """Get a valid installation access token, using cache or fetching new."""
    cached = installation_token_cache.get(installation_id)
    if cached:
        return cached

    app_jwt = generate_jwt(settings.GITHUB_APP_ID or "", settings.github_app_private_key_pem)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_jwt}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    if response.is_error:
        raise GitHubAppError(f"Failed to get installation token: {response.text}")

    data = response.json()
    token = data["token"]
    # GitHub tokens expire in 1 hour
    expires_at = time.time() + 3600
    installation_token_cache.set(installation_id, token, expires_at)
    return token  # type: ignore[no-any-return]


class GitHubAppClient:
    """Client for making authenticated GitHub API calls as a GitHub App installation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _get_headers(self, installation_id: int) -> dict[str, str]:
        token = await get_installation_token(installation_id, self.settings)
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_repositories(
        self, installation_id: int, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """List repositories accessible to the installation."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.settings.GITHUB_API_URL}/installation/repositories",
                headers=await self._get_headers(installation_id),
                params={"per_page": per_page},
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to list repositories: {response.text}")
        return response.json().get("repositories", [])  # type: ignore[no-any-return]

    async def get_workflow_run_logs(
        self, installation_id: int, owner: str, repo: str, run_id: int
    ) -> str:
        """Fetch workflow run logs."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/actions/runs/{run_id}/logs",
                headers=await self._get_headers(installation_id),
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to fetch workflow logs: {response.text}")
        return response.text

    async def get_workflow_run(
        self, installation_id: int, owner: str, repo: str, run_id: int
    ) -> dict[str, Any]:
        """Get workflow run details."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/actions/runs/{run_id}",
                headers=await self._get_headers(installation_id),
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to get workflow run: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def get_compare(
        self, installation_id: int, owner: str, repo: str, base: str, head: str
    ) -> dict[str, Any]:
        """Get compare/diff between two commits."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/compare/{base}...{head}",
                headers=await self._get_headers(installation_id),
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to get compare: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def create_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """Create a pull request."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
                headers=await self._get_headers(installation_id),
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to create PR: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def create_ref(
        self, installation_id: int, owner: str, repo: str, ref: str, sha: str
    ) -> dict[str, Any]:
        """Create a git reference (branch)."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/git/refs",
                headers=await self._get_headers(installation_id),
                json={"ref": f"refs/heads/{ref}", "sha": sha},
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to create ref: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def create_commit(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        message: str,
        tree_sha: str,
        parent_shas: list[str],
    ) -> dict[str, Any]:
        """Create a commit."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/git/commits",
                headers=await self._get_headers(installation_id),
                json={
                    "message": message,
                    "tree": tree_sha,
                    "parents": parent_shas,
                },
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to create commit: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def create_tree(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        tree: list[dict[str, Any]],
        base_tree: str | None = None,
    ) -> dict[str, Any]:
        """Create a tree."""
        async with httpx.AsyncClient(timeout=15) as client:
            payload: dict[str, Any] = {"tree": tree}
            if base_tree:
                payload["base_tree"] = base_tree
            response = await client.post(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/git/trees",
                headers=await self._get_headers(installation_id),
                json=payload,
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to create tree: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def create_blob(
        self, installation_id: int, owner: str, repo: str, content: str, encoding: str = "utf-8"
    ) -> dict[str, Any]:
        """Create a blob."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/git/blobs",
                headers=await self._get_headers(installation_id),
                json={"content": content, "encoding": encoding},
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to create blob: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def get_file_content(
        self, installation_id: int, owner: str, repo: str, path: str, ref: str
    ) -> dict[str, Any] | None:
        """Get file content."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=await self._get_headers(installation_id),
                params={"ref": ref},
            )
        if response.status_code == 404:
            return None
        if response.is_error:
            raise GitHubAppError(f"Failed to get file content: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def request_reviewers(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        reviewers: list[str],
    ) -> dict[str, Any]:
        """Request reviewers on a PR."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
                headers=await self._get_headers(installation_id),
                json={"reviewers": reviewers},
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to request reviewers: {response.text}")
        return response.json()  # type: ignore[no-any-return]

    async def merge_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        """Merge a pull request."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.put(
                f"{self.settings.GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                headers=await self._get_headers(installation_id),
                json={"merge_method": merge_method},
            )
        if response.is_error:
            raise GitHubAppError(f"Failed to merge PR: {response.text}")
        return response.json()  # type: ignore[no-any-return]


def create_installation_state(workspace_id: str, user_id: str, settings: Settings) -> str:
    """Create a signed state token for GitHub App installation flow."""
    payload = {"workspace_id": workspace_id, "user_id": user_id}
    return create_token(
        subject=json.dumps(payload),
        kind=TokenKind.OAUTH_STATE,
        lifetime=timedelta(minutes=10),
        settings=settings,
    )


def parse_installation_state(state: str, settings: Settings) -> tuple[str, str]:
    """Parse and validate installation state token."""
    claims = decode_token(state, expected_kind=TokenKind.OAUTH_STATE, settings=settings)
    data = json.loads(claims.sub)
    return data["workspace_id"], data["user_id"]


@dataclass
class GitHubAppInstallation:
    """Handles GitHub App installation flow."""

    settings: Settings
    cipher: SecretCipher

    async def initiate_installation(self, workspace_id: str, user_id: str) -> str:
        """Generate the GitHub App installation URL with state."""
        state = create_installation_state(workspace_id, user_id, self.settings)
        params = {"state": state}
        return f"{self.settings.github_app_install_url}?{urlencode(params)}"

    async def handle_callback(
        self, installation_id: int, state: str, setup_action: str | None
    ) -> tuple[Workspace, str]:
        """Process the installation callback, store installation ID on workspace."""
        workspace_id, user_id = parse_installation_state(state, self.settings)

        workspace = await Workspace.get(PydanticObjectId(workspace_id))
        if not workspace:
            raise GitHubAppError("Workspace not found")

        # Verify ownership
        if str(workspace.owner_id) != user_id:
            raise GitHubAppError("Workspace ownership mismatch")

        # Fetch installation details to get repo info
        client = GitHubAppClient(self.settings)
        try:
            repos = await client.get_repositories(installation_id)
        except GitHubAppError:
            repos = []

        # Update workspace with installation info
        workspace.github_installation_id = installation_id
        if repos:
            # For now, use the first repo as primary
            repo = repos[0]
            workspace.github_repository_id = repo["id"]
            workspace.github_repo_full_name = repo["full_name"]
            workspace.github_default_branch = repo.get("default_branch", "main")
            workspace.github_repo_private = repo.get("private", False)
            workspace.github_repo_html_url = repo.get("html_url")
            workspace.github_account_login = repo.get("owner", {}).get("login")
            workspace.github_account_type = repo.get("owner", {}).get("type")
        workspace.connected_at = utc_now()
        await workspace.save()

        return workspace, setup_action or "install"

    async def disconnect_installation(self, workspace: Workspace) -> None:
        """Remove GitHub App installation from workspace."""
        workspace.github_installation_id = None
        workspace.github_repository_id = None
        workspace.github_repo_full_name = None
        workspace.github_default_branch = None
        workspace.github_repo_private = None
        workspace.github_repo_html_url = None
        workspace.github_account_login = None
        workspace.github_account_type = None
        workspace.connected_at = None
        await workspace.save()
