import os
from typing import Any
from uuid import uuid4

import pytest

from pipelineiq.config import Settings
from pipelineiq.database import close_database, connect_database, database_state
from pipelineiq.models import PipelineRun, User, WebhookEvent, Workspace
from pipelineiq.services.github_webhooks import (
    GitHubWebhookPayload,
    MongoWebhookStore,
    WebhookIntake,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("PIPELINEIQ_RUN_INTEGRATION") != "1",
        reason="set PIPELINEIQ_RUN_INTEGRATION=1 to run MongoDB integration tests",
    ),
]


def workflow_payload() -> dict[str, Any]:
    return {
        "action": "completed",
        "workflow_run": {
            "id": 778899,
            "name": "CI",
            "status": "completed",
            "head_branch": "feature/integration",
            "head_sha": "abc123",
            "conclusion": "failure",
            "triggering_actor": {"login": "octocat"},
        },
        "repository": {"id": 445566, "full_name": "acme/service"},
        "installation": {"id": 112233},
    }


@pytest.mark.asyncio
async def test_webhook_delivery_is_persisted_once() -> None:
    database_name = f"pipelineiq_test_{uuid4().hex}"
    settings = Settings(
        MONGODB_DB_NAME=database_name,
        DATABASE_REQUIRED_AT_STARTUP=True,
    )

    assert await connect_database(settings)
    assert database_state.client is not None
    try:
        user = await User(
            github_id=1,
            username="octocat",
            github_access_token="encrypted-test-token",
        ).insert()
        assert user.id is not None
        workspace = await Workspace(
            name="Integration workspace",
            owner_id=user.id,
            github_installation_id=112233,
        ).insert()
        assert workspace.id is not None

        raw_payload = workflow_payload()
        intake = WebhookIntake(store=MongoWebhookStore())
        first = await intake.process(
            delivery_id="integration-delivery",
            event_type="workflow_run",
            payload=GitHubWebhookPayload.model_validate(raw_payload),
            raw_payload=raw_payload,
        )
        second = await intake.process(
            delivery_id="integration-delivery",
            event_type="workflow_run",
            payload=GitHubWebhookPayload.model_validate(raw_payload),
            raw_payload=raw_payload,
        )

        assert not first.duplicate
        assert second.duplicate
        assert await WebhookEvent.count() == 1
        assert await PipelineRun.count() == 1
        persisted_run = await PipelineRun.find_one(
            PipelineRun.delivery_id == "integration-delivery"
        )
        assert persisted_run is not None
        assert persisted_run.health_status == "failed"
    finally:
        await database_state.client.drop_database(database_name)
        close_database()
