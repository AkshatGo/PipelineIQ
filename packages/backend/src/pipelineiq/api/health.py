from fastapi import APIRouter

from pipelineiq import __version__
from pipelineiq.config import get_settings
from pipelineiq.contracts import HealthResponse, ReadinessResponse

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
    # Connectivity checks are added when persistence starts in Phase 2. Reporting
    # disabled optional services now makes local behavior explicit and stable.
    checks = {
        "api": "ready",
        "database": "configured",
        "kafka": "configured" if settings.KAFKA_ENABLED else "disabled",
        "slack": "configured" if settings.SLACK_ENABLED else "disabled",
    }
    return ReadinessResponse(status="ready", checks=checks)
