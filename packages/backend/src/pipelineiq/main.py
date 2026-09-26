from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from pipelineiq import __version__
from pipelineiq.api.github import router as github_router
from pipelineiq.api.health import router as health_router
from pipelineiq.api.risk import router as risk_router
from pipelineiq.config import get_settings
from pipelineiq.database import close_database, connect_database
from pipelineiq.errors import (
    PipelineIQError,
    error_response,
    pipelineiq_error_handler,
    validation_error_handler,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("application_started", environment=settings.APP_ENV, version=__version__)
    if settings.DATABASE_CONNECT_ON_STARTUP:
        await connect_database(settings)
    yield
    close_database()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="AI-powered CI/CD failure intelligence and auto-remediation API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(risk_router, prefix=settings.API_PREFIX)
    application.include_router(github_router)
    application.add_exception_handler(PipelineIQError, pipelineiq_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

    @application.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id[:128]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {"message": "PipelineIQ API is running"}

    @application.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
        return error_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="Unexpected error",
        )

    return application


app = create_app()
