import pytest
from httpx import ASGITransport, AsyncClient

from pipelineiq.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "PipelineIQ",
        "version": "0.1.0",
        "environment": "development",
    }


@pytest.mark.asyncio
async def test_readiness_exposes_optional_services() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["kafka"] == "disabled"
