from fastapi import APIRouter

from pipelineiq import __version__
from pipelineiq.config import get_settings
from pipelineiq.contracts import HealthResponse, ReadinessResponse
from pipelineiq.database import database_state

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        version=__version__,
        environment=settings.APP_ENV,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    settings = get_settings()
    checks = {
        "api": "ready",
        "database": "ready" if database_state.ready else "unavailable",
        "kafka": "configured" if settings.KAFKA_ENABLED else "disabled",
        "slack": "configured" if settings.SLACK_ENABLED else "disabled",
    }
    status = "ready" if database_state.ready else "degraded"
    return ReadinessResponse(status=status, checks=checks)
