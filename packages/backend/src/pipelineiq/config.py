from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env.local."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ROOT_DIR / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "PipelineIQ"
    APP_ENV: Literal["development", "test", "staging", "production"] = "development"
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:5173"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pipelineiq"
    DATABASE_REQUIRED_AT_STARTUP: bool = False

    JWT_SECRET: str = Field(default="development-only-change-me-32-chars", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRY_DAYS: int = Field(default=15, ge=1, le=90)

    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/auth/github/callback"
    GITHUB_APP_ID: str | None = None
    GITHUB_APP_SLUG: str | None = None
    GITHUB_APP_PRIVATE_KEY: str | None = None
    GITHUB_APP_WEBHOOK_SECRET: str | None = None

    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    SLACK_ENABLED: bool = False
    SLACK_WEBHOOK_URL: str | None = None

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

