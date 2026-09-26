import hashlib
import hmac
from typing import Any

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from pipelineiq.services.github_webhooks import (
    GitHubWebhookPayload,
    NormalizedPipelineEvent,
    WebhookIntake,
    WorkspaceReference,
    verify_webhook_signature,
)


class FakeWebhookStore:
    def __init__(self, *, connected: bool = True, created: bool = True) -> None:
        self.connected = connected
        self.created = created
        self.saved_event: NormalizedPipelineEvent | None = None

    async def find_workspace(self, installation_id: int) -> WorkspaceReference | None:
        if not self.connected:
            return None
        return WorkspaceReference(
            id=PydanticObjectId("66f8a1b2c3d4e5f6a7b8c9d1"),
            installation_id=installation_id,
        )

    async def save(
        self,
        workspace: WorkspaceReference,
        event: NormalizedPipelineEvent,
        raw_payload: dict[str, Any],
    ) -> bool:
        del workspace, raw_payload
        self.saved_event = event
        return self.created


def workflow_payload(*, action: str = "completed", conclusion: str = "failure") -> dict[str, Any]:
    return {
        "action": action,
        "workflow_run": {
            "id": 12345,
            "name": "CI Pipeline",
            "status": "completed",
            "head_branch": "feature/xyz",
            "head_sha": "abcdef1234567890",
            "conclusion": conclusion,
            "html_url": "https://github.com/acme/app/actions/runs/12345",
            "triggering_actor": {"login": "octocat"},
        },
        "repository": {
            "id": 987654321,
            "full_name": "acme/app",
            "private": True,
            "default_branch": "main",
        },
        "installation": {"id": 12345678},
        "sender": {"login": "octocat"},
    }


def test_signature_verification_uses_expected_digest() -> None:
    body = b'{"action":"completed"}'
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(body, signature, "secret")
    assert not verify_webhook_signature(body + b" ", signature, "secret")
    assert not verify_webhook_signature(body, None, "secret")
    assert not verify_webhook_signature(body, "sha1=legacy", "secret")


@pytest.mark.asyncio
async def test_completed_failure_is_normalized_and_saved() -> None:
    store = FakeWebhookStore()
    payload_dict = workflow_payload()

    receipt = await WebhookIntake(store=store).process(
        delivery_id="delivery-1",
        event_type="workflow_run",
        payload=GitHubWebhookPayload.model_validate(payload_dict),
        raw_payload=payload_dict,
    )

    assert receipt.received
    assert receipt.workspace_id == "66f8a1b2c3d4e5f6a7b8c9d1"
    assert receipt.kafka_topic == "pipeline-events"
    assert store.saved_event is not None
    assert store.saved_event.health_status == "failed"
    assert store.saved_event.triggered_by == "octocat"


@pytest.mark.asyncio
async def test_non_completed_workflow_is_ignored_without_store_access() -> None:
    store = FakeWebhookStore(connected=False)
    payload_dict = workflow_payload(action="requested")

    receipt = await WebhookIntake(store=store).process(
        delivery_id="delivery-2",
        event_type="workflow_run",
        payload=GitHubWebhookPayload.model_validate(payload_dict),
        raw_payload=payload_dict,
    )

    assert receipt.ignored == "workflow_not_completed"
    assert store.saved_event is None


@pytest.mark.asyncio
async def test_duplicate_delivery_is_acknowledged_without_requeue() -> None:
    store = FakeWebhookStore(created=False)
    payload_dict = workflow_payload(conclusion="success")

    receipt = await WebhookIntake(store=store).process(
        delivery_id="delivery-3",
        event_type="workflow_run",
        payload=GitHubWebhookPayload.model_validate(payload_dict),
        raw_payload=payload_dict,
    )

    assert receipt.duplicate
    assert receipt.kafka_topic is None
    assert store.saved_event is not None
    assert store.saved_event.health_status == "healthy"


@pytest.mark.asyncio
async def test_unknown_installation_is_rejected() -> None:
    payload_dict = workflow_payload()

    with pytest.raises(LookupError):
        await WebhookIntake(store=FakeWebhookStore(connected=False)).process(
            delivery_id="delivery-4",
            event_type="workflow_run",
            payload=GitHubWebhookPayload.model_validate(payload_dict),
            raw_payload=payload_dict,
        )


def test_installation_id_is_required_for_tracked_workflow() -> None:
    payload = workflow_payload()
    del payload["installation"]
    parsed = GitHubWebhookPayload.model_validate(payload)

    assert parsed.installation is None
    with pytest.raises(ValidationError):
        WorkspaceReference.model_validate({"id": "invalid", "installation_id": 1})
