"""GitHub App installation flow handling."""

import json
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from beanie import PydanticObjectId

from pipelineiq.auth.crypto import SecretCipher
from pipelineiq.auth.tokens import TokenKind, create_token, decode_token
from pipelineiq.config import Settings
from pipelineiq.errors import PipelineIQError as GitHubAppError
from pipelineiq.github.github_app_client import GitHubAppClient
from pipelineiq.models import Workspace, utc_now


class GitHubAppInstallationError(GitHubAppError):
    """Custom exception for GitHub App installation errors."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(status_code=status_code, code=code, message=message)


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
            raise GitHubAppInstallationError(
                code="WORKSPACE_NOT_FOUND",
                message="Workspace not found",
                status_code=404,
            )

        # Verify ownership
        if str(workspace.owner_id) != user_id:
            raise GitHubAppInstallationError(
                code="OWNERSHIP_MISMATCH",
                message="Workspace ownership mismatch",
                status_code=403,
            )

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