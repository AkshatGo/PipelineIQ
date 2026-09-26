import json
from typing import Annotated, Any

from fastapi import APIRouter, Header, Request, status
from pydantic import ValidationError

from pipelineiq.config import get_settings
from pipelineiq.database import database_state
from pipelineiq.errors import PipelineIQError
from pipelineiq.services.github_webhooks import (
    GitHubWebhookPayload,
    MongoWebhookStore,
    WebhookIntake,
    WebhookReceipt,
    verify_webhook_signature,
)

router = APIRouter(tags=["github"])


async def get_webhook_intake() -> WebhookIntake:
    if not database_state.ready:
        raise PipelineIQError(
            status_code=503,
            code="DB_UNAVAILABLE",
            message="Webhook persistence is temporarily unavailable",
        )
    return WebhookIntake(store=MongoWebhookStore())


@router.post(
    "/api/github/webhooks",
    response_model=WebhookReceipt,
    status_code=status.HTTP_202_ACCEPTED,
)
@router.post(
    "/webhook/github",
    response_model=WebhookReceipt,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def receive_github_webhook(
    request: Request,
    x_github_event: Annotated[str, Header(min_length=1)],
    x_github_delivery: Annotated[str, Header(min_length=1, max_length=255)],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> WebhookReceipt:
    settings = get_settings()
    content_length = request.headers.get("content-length")
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > settings.GITHUB_WEBHOOK_MAX_BYTES
    ):
        raise PipelineIQError(
            status_code=413,
            code="GITHUB_WEBHOOK_TOO_LARGE",
            message="Webhook payload exceeds the configured size limit",
        )
    body = await request.body()
    if len(body) > settings.GITHUB_WEBHOOK_MAX_BYTES:
        raise PipelineIQError(
            status_code=413,
            code="GITHUB_WEBHOOK_TOO_LARGE",
            message="Webhook payload exceeds the configured size limit",
        )
    if not settings.GITHUB_APP_WEBHOOK_SECRET:
        raise PipelineIQError(
            status_code=503,
            code="GITHUB_WEBHOOK_NOT_CONFIGURED",
            message="GitHub webhook processing is not configured",
        )
    if not verify_webhook_signature(body, x_hub_signature_256, settings.GITHUB_APP_WEBHOOK_SECRET):
        raise PipelineIQError(
            status_code=401,
            code="GITHUB_WEBHOOK_INVALID_SIGNATURE",
            message="Invalid webhook signature",
        )

    try:
        raw_payload: dict[str, Any] = json.loads(body)
        payload = GitHubWebhookPayload.model_validate(raw_payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError, TypeError) as exc:
        raise PipelineIQError(
            status_code=400,
            code="GITHUB_WEBHOOK_INVALID_PAYLOAD",
            message="Webhook payload is not valid JSON for this event",
        ) from exc

    intake = await get_webhook_intake()
    try:
        return await intake.process(
            delivery_id=x_github_delivery,
            event_type=x_github_event,
            payload=payload,
            raw_payload=raw_payload,
        )
    except LookupError as exc:
        raise PipelineIQError(
            status_code=404,
            code="GITHUB_INSTALLATION_NOT_CONNECTED",
            message=str(exc),
        ) from exc
    except ValueError as exc:
        raise PipelineIQError(
            status_code=422,
            code="GITHUB_WEBHOOK_UNPROCESSABLE",
            message=str(exc),
        ) from exc
