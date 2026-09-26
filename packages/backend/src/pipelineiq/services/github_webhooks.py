import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Protocol

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict
from pymongo.errors import DuplicateKeyError

from pipelineiq.models import PipelineRun, WebhookEvent, Workspace, utc_now

IGNORED_GITHUB_EVENTS = {"installation", "installation_repositories", "installation_target"}


def verify_webhook_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


class GitHubActor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    login: str | None = None


class GitHubInstallation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int


class GitHubRepository(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    full_name: str
    private: bool = False
    html_url: str | None = None
    default_branch: str = "main"


class GitHubWorkflowRun(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    name: str | None = None
    status: str | None = None
    conclusion: str | None = None
    head_branch: str | None = None
    head_sha: str | None = None
    html_url: str | None = None
    triggering_actor: GitHubActor | None = None


class GitHubWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    action: str | None = None
    installation: GitHubInstallation | None = None
    repository: GitHubRepository | None = None
    workflow_run: GitHubWorkflowRun | None = None
    sender: GitHubActor | None = None


class WorkspaceReference(BaseModel):
    id: PydanticObjectId
    installation_id: int


class NormalizedPipelineEvent(BaseModel):
    delivery_id: str
    event_type: str
    action: str | None = None
    installation_id: int
    repository_full_name: str
    run_id: int | None = None
    workflow_status: str | None = None
    workflow_name: str | None = None
    workflow_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    triggered_by: str | None = None
    conclusion: str | None = None
    health_status: str = "unknown"


class WebhookReceipt(BaseModel):
    received: bool = True
    event_type: str
    delivery_id: str
    ignored: str | None = None
    duplicate: bool = False
    workspace_id: str | None = None
    repo: str | None = None
    run_id: int | None = None
    conclusion: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    triggered_by: str | None = None
    kafka_topic: str | None = None


class WebhookStore(Protocol):
    async def find_workspace(self, installation_id: int) -> WorkspaceReference | None: ...

    async def save(
        self,
        workspace: WorkspaceReference,
        event: NormalizedPipelineEvent,
        raw_payload: dict[str, Any],
    ) -> bool: ...


class MongoWebhookStore:
    async def find_workspace(self, installation_id: int) -> WorkspaceReference | None:
        workspace = await Workspace.find_one(Workspace.github_installation_id == installation_id)
        if workspace is None or workspace.id is None:
            return None
        return WorkspaceReference(id=workspace.id, installation_id=installation_id)

    async def save(
        self,
        workspace: WorkspaceReference,
        event: NormalizedPipelineEvent,
        raw_payload: dict[str, Any],
    ) -> bool:
        webhook = WebhookEvent(
            delivery_id=event.delivery_id,
            event_type=event.event_type,
            action=event.action,
            installation_id=event.installation_id,
            repository_full_name=event.repository_full_name,
            payload=raw_payload,
        )
        try:
            await webhook.insert()
        except DuplicateKeyError:
            existing_run = await PipelineRun.find_one(PipelineRun.delivery_id == event.delivery_id)
            if existing_run is not None:
                return False

        pipeline_run = PipelineRun(
            workspace_id=workspace.id,
            installation_id=event.installation_id,
            repository_full_name=event.repository_full_name,
            delivery_id=event.delivery_id,
            event_type=event.event_type,
            action=event.action,
            run_id=event.run_id,
            workflow_status=event.workflow_status,
            workflow_name=event.workflow_name,
            workflow_url=event.workflow_url,
            branch=event.branch,
            commit_sha=event.commit_sha,
            triggered_by=event.triggered_by,
            conclusion=event.conclusion,
            health_status=event.health_status,
            raw_event=raw_payload,
            enriched_event=event.model_dump(mode="json"),
        )
        try:
            await pipeline_run.insert()
        except DuplicateKeyError:
            return False
        await Workspace.find_one(Workspace.id == workspace.id).update(
            {"$set": {"last_webhook_event_at": utc_now(), "updated_at": utc_now()}}
        )
        return True


@dataclass
class WebhookIntake:
    store: WebhookStore

    async def process(
        self,
        *,
        delivery_id: str,
        event_type: str,
        payload: GitHubWebhookPayload,
        raw_payload: dict[str, Any],
    ) -> WebhookReceipt:
        if event_type in IGNORED_GITHUB_EVENTS:
            return WebhookReceipt(
                event_type=event_type,
                delivery_id=delivery_id,
                ignored="non_ci_event",
            )
        if event_type != "workflow_run":
            return WebhookReceipt(
                event_type=event_type,
                delivery_id=delivery_id,
                ignored="unsupported_event",
            )
        if payload.action != "completed":
            return WebhookReceipt(
                event_type=event_type,
                delivery_id=delivery_id,
                ignored="workflow_not_completed",
            )
        if (
            payload.installation is None
            or payload.repository is None
            or payload.workflow_run is None
        ):
            raise ValueError("workflow_run payload is missing required GitHub objects")

        workspace = await self.store.find_workspace(payload.installation.id)
        if workspace is None:
            raise LookupError("No workspace matches this GitHub installation")

        run = payload.workflow_run
        actor = run.triggering_actor or payload.sender
        event = NormalizedPipelineEvent(
            delivery_id=delivery_id,
            event_type=event_type,
            action=payload.action,
            installation_id=payload.installation.id,
            repository_full_name=payload.repository.full_name,
            run_id=run.id,
            workflow_status=run.status,
            workflow_name=run.name,
            workflow_url=run.html_url,
            branch=run.head_branch,
            commit_sha=run.head_sha,
            triggered_by=actor.login if actor else None,
            conclusion=run.conclusion,
            health_status="failed" if run.conclusion == "failure" else "healthy",
        )
        created = await self.store.save(workspace, event, raw_payload)
        return WebhookReceipt(
            event_type=event_type,
            delivery_id=delivery_id,
            duplicate=not created,
            workspace_id=str(workspace.id),
            repo=event.repository_full_name,
            run_id=event.run_id,
            conclusion=event.conclusion,
            branch=event.branch,
            commit_sha=event.commit_sha,
            triggered_by=event.triggered_by,
            kafka_topic="pipeline-events" if created else None,
        )
