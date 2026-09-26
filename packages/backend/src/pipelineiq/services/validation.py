"""Validation Service: CI/CD validation orchestration with GitHub Actions integration."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from beanie import PydanticObjectId

from pipelineiq.config import Settings
from pipelineiq.github.github_app_client import GitHubAppClient
from pipelineiq.models import ValidationRun, utc_now
from pipelineiq.services.audit import get_audit_service
from pipelineiq.services.workspaces import get_collaborative_workspace_by_incident


class GitHubClientProtocol(Protocol):
    """Protocol defining the GitHub client interface needed by ValidationService."""

    async def create_file(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> dict[str, Any] | None: ...

    async def dispatch_workflow(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str,
        inputs: dict[str, str] | None = None,
    ) -> dict[str, Any] | None: ...

    async def get_workflow_runs(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        workflow_id: str,
        branch: str,
        per_page: int = 10,
    ) -> list[dict[str, Any]]: ...


class ValidationService:
    """Service for orchestrating CI/CD validation runs via GitHub Actions."""

    DEFAULT_STAGES = [
        {"name": "lint", "command": "npm run lint", "required": True, "timeout": 60000},
        {"name": "typecheck", "command": "npm run typecheck", "required": True, "timeout": 60000},
        {"name": "test", "command": "npm test", "required": True, "timeout": 180000},
        {"name": "build", "command": "npm run build", "required": True, "timeout": 120000},
    ]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: GitHubClientProtocol = GitHubAppClient(settings)  # type: ignore[assignment]

    async def create_workflow_file(
        self,
        workspace_id: PydanticObjectId,
        custom_stages: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate a GitHub Actions workflow YAML for validation."""
        stages = custom_stages or self.DEFAULT_STAGES

        workflow_yaml = """name: PipelineIQ Validation

on:
  workflow_dispatch:
    inputs:
      validation_run_id:
        description: 'Validation Run ID'
        required: true
        type: string

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

"""

        for stage in stages:
            timeout_value = stage["timeout"]
            timeout_minutes = timeout_value // 60000 if isinstance(timeout_value, int) else 5
            workflow_yaml += f"""      - name: {stage['name']}
        run: {stage['command']}
        timeout-minutes: {timeout_minutes}

"""

        workflow_yaml += """      - name: Upload validation artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: validation-results
          path: |
            coverage/
            dist/
            .next/
"""

        return workflow_yaml

    async def trigger_validation(
        self,
        validation_run: ValidationRun,
        workspace_id: PydanticObjectId,
        custom_stages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Trigger a GitHub Actions validation workflow."""
        workspace = await get_collaborative_workspace_by_incident(
            validation_run.workspace_id,
            validation_run.workspace_id,
        )
        if not workspace or not workspace.github_installation_id:
            return None

        assert workspace.id is not None
        workflow_content = await self.create_workflow_file(workspace.id, custom_stages)

        owner, repo = workspace.repository_full_name.split("/", 1)

        workflow_path = f".github/workflows/pipelineiq-validation-{validation_run.id}.yml"

        try:
            await self.client.create_file(
                installation_id=workspace.github_installation_id,
                owner=owner,
                repo=repo,
                path=workflow_path,
                content=workflow_content,
                message=f"PipelineIQ: Add validation workflow for run {validation_run.id}",
                branch=workspace.head_branch,
            )

            dispatch_result = await self.client.dispatch_workflow(
                installation_id=workspace.github_installation_id,
                owner=owner,
                repo=repo,
                workflow_id=workflow_path,
                ref=workspace.head_branch,
                inputs={"validation_run_id": str(validation_run.id)},
            )

            return dispatch_result
        except Exception:
            return None

    async def poll_validation_status(
        self,
        validation_run: ValidationRun,
        max_wait_seconds: int = 1800,
        poll_interval: int = 30,
    ) -> dict[str, Any]:
        """Poll GitHub Actions for validation completion."""
        workspace = await get_collaborative_workspace_by_incident(
            validation_run.workspace_id,
            validation_run.workspace_id,
        )
        if not workspace or not workspace.github_installation_id:
            return {"status": "error", "error": "No GitHub installation"}

        owner, repo = workspace.repository_full_name.split("/", 1)

        elapsed = 0
        while elapsed < max_wait_seconds:
            try:
                runs = await self.client.get_workflow_runs(
                    installation_id=workspace.github_installation_id,
                    owner=owner,
                    repo=repo,
                    workflow_id=f"pipelineiq-validation-{validation_run.id}.yml",
                    branch=workspace.head_branch,
                )

                if runs:
                    latest_run = runs[0]
                    status = latest_run.get("conclusion")

                    if status in ("success", "failure", "cancelled"):
                        return {
                            "status": status,
                            "run_id": latest_run.get("id"),
                            "html_url": latest_run.get("html_url"),
                            "logs_url": f"{latest_run.get('html_url')}/logs",
                        }
            except Exception:
                pass

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        return {"status": "timeout", "error": "Validation timed out"}

    async def run_validation_pipeline(
        self,
        workspace_id: PydanticObjectId,
        version_id: PydanticObjectId,
        triggered_by: PydanticObjectId,
    ) -> ValidationRun:
        """Execute the full validation pipeline."""
        from pipelineiq.models import ValidationRun

        validation_run = ValidationRun(
            workspace_id=workspace_id,
            version_id=version_id,
            triggered_by=triggered_by,
            status="pending",
            stages=[],
        )
        await validation_run.insert()

        validation_run.status = "running"
        validation_run.started_at = utc_now()
        await validation_run.save()

        from pipelineiq.models import CollaborativeWorkspace
        workspace = await CollaborativeWorkspace.get(workspace_id)
        if not workspace:
            validation_run.status = "failed"
            validation_run.completed_at = utc_now()
            await validation_run.save()
            return validation_run

        dispatch_result = await self.trigger_validation(validation_run, workspace_id)

        if not dispatch_result:
            validation_run.status = "failed"
            validation_run.completed_at = utc_now()
            validation_run.stages.append({
                "name": "dispatch",
                "status": "failed",
                "error": "Failed to trigger GitHub Actions workflow",
            })
            validation_run.completed_at = utc_now()
            await validation_run.save()

            assert validation_run.id is not None

            audit = get_audit_service()
            await audit.log_validation_completed(
                incident_id=validation_run.workspace_id,
                workspace_id=workspace_id,
                validation_run_id=validation_run.id,
                status="failed",
                stage_results=[{"name": "dispatch", "status": "failed"}],
            )
            return validation_run

        result = await self.poll_validation_status(validation_run)

        assert validation_run.id is not None

        if result.get("status") == "success":
            validation_run.status = "passed"
        elif result.get("status") == "failure":
            validation_run.status = "failed"
        else:
            validation_run.status = "failed"

        validation_run.completed_at = utc_now()
        await validation_run.save()

        audit = get_audit_service()
        stage_results = [{"name": "github_actions", "status": result.get("status", "unknown")}]
        await audit.log_validation_completed(
            incident_id=validation_run.workspace_id,
            workspace_id=workspace_id,
            validation_run_id=validation_run.id,
            status=validation_run.status,
            stage_results=stage_results,
        )

        return validation_run


# Global instance
_validation_service: ValidationService | None = None


def get_validation_service(settings: Settings) -> ValidationService:
    """Get or create the global validation service instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService(settings)
    return _validation_service