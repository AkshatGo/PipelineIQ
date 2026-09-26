from dataclasses import dataclass
from typing import Any

import structlog
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from pipelineiq.config import Settings
from pipelineiq.models import DOCUMENT_MODELS

logger = structlog.get_logger()


@dataclass
class DatabaseState:
    client: AsyncIOMotorClient[dict[str, Any]] | None = None
    ready: bool = False
    error: str | None = None


database_state = DatabaseState()


async def connect_database(settings: Settings) -> bool:
    client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=settings.DATABASE_CONNECT_TIMEOUT_MS,
    )
    try:
        await client.admin.command("ping")
        await init_beanie(
            database=client[settings.MONGODB_DB_NAME],
            document_models=DOCUMENT_MODELS,
        )
    except Exception as exc:
        client.close()
        database_state.client = None
        database_state.ready = False
        database_state.error = type(exc).__name__
        logger.warning("database_connection_failed", error=type(exc).__name__)
        if settings.DATABASE_REQUIRED_AT_STARTUP:
            raise
        return False

    database_state.client = client
    database_state.ready = True
    database_state.error = None
    logger.info("database_connected", database=settings.MONGODB_DB_NAME)
    return True


def close_database() -> None:
    if database_state.client is not None:
        database_state.client.close()
    database_state.client = None
    database_state.ready = False

