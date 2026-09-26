import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from pipelineiq.config import get_settings
from pipelineiq.main import app


def signature(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_APP_WEBHOOK_SECRET", "test-webhook-secret")
    get_settings.cache_clear()
    body = json.dumps({"action": "completed"}).encode()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/github/webhooks",
                content=body,
                headers={
                    "X-GitHub-Event": "workflow_run",
                    "X-GitHub-Delivery": "delivery-invalid",
                    "X-Hub-Signature-256": signature(body, "wrong-secret"),
                    "Content-Type": "application/json",
                },
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GITHUB_WEBHOOK_INVALID_SIGNATURE"
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_webhook_requires_configuration() -> None:
    get_settings.cache_clear()
    body = b"{}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/github/webhooks",
            content=body,
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "delivery-unconfigured",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GITHUB_WEBHOOK_NOT_CONFIGURED"

