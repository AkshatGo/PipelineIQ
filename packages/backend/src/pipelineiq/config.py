from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_root_dir() -> Path:
    """Find the project root directory by looking for pyproject.toml or .git directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        current = current.parent
    # Fallback to current working directory
    return Path.cwd()


ROOT_DIR = find_root_dir()


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
    DATABASE_CONNECT_ON_STARTUP: bool = True
    DATABASE_REQUIRED_AT_STARTUP: bool = False
    DATABASE_CONNECT_TIMEOUT_MS: int = Field(default=2000, ge=250, le=30000)

    JWT_SECRET: str = Field(default="development-only-change-me-32-chars", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRY_DAYS: int = Field(default=15, ge=1, le=90)
    SESSION_COOKIE_NAME: str = "piq_session"
    OAUTH_STATE_COOKIE_NAME: str = "piq_oauth_state"
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: str | None = None
    ENCRYPTION_KEY: str | None = None

    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/auth/github/callback"
    GITHUB_OAUTH_SCOPES: str = "read:user read:org"
    GITHUB_AUTHORIZE_URL: str = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL: str = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_APP_ID: str | None = None
    GITHUB_APP_SLUG: str | None = None
    GITHUB_APP_PRIVATE_KEY: str | None = None
    GITHUB_APP_WEBHOOK_SECRET: str | None = None
    GITHUB_WEBHOOK_MAX_BYTES: int = Field(default=10_000_000, ge=1024)

    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    SLACK_ENABLED: bool = False
    SLACK_WEBHOOK_URL: str | None = None

    # LLM Provider settings
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
    GROQ_API_KEY: str | None = None
    GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"
    GITHUB_TOKEN: str | None = None
    GITHUB_MODELS_API_BASE_URL: str = "https://models.github.ai/inference"

    # Agent provider configuration
    MONITOR_AGENT_PRIMARY_PROVIDER: str = "github_models"
    MONITOR_AGENT_PRIMARY_MODEL: str = "gpt-4o-mini"
    MONITOR_AGENT_FALLBACK_PROVIDER: str = "groq"
    MONITOR_AGENT_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"

    DIAGNOSIS_AGENT_PRIMARY_PROVIDER: str = "groq"
    DIAGNOSIS_AGENT_PRIMARY_MODEL: str = "llama-3.3-70b-versatile"
    DIAGNOSIS_AGENT_FALLBACK_PROVIDER: str = "github_models"
    DIAGNOSIS_AGENT_FALLBACK_MODEL: str = "gpt-4o-mini"

    RISK_AGENT_PRIMARY_PROVIDER: str = "github_models"
    RISK_AGENT_PRIMARY_MODEL: str = "gpt-4o-mini"
    RISK_AGENT_FALLBACK_PROVIDER: str = "groq"
    RISK_AGENT_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"

    AUTOFIX_AGENT_PRIMARY_PROVIDER: str = "github_models"
    AUTOFIX_AGENT_PRIMARY_MODEL: str = "gpt-4o-mini"
    AUTOFIX_AGENT_FALLBACK_PROVIDER: str = "groq"
    AUTOFIX_AGENT_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"

    @model_validator(mode="after")
    def enforce_production_security(self) -> "Settings":
        if self.APP_ENV != "production":
            return self
        missing: list[str] = []
        if self.JWT_SECRET == "development-only-change-me-32-chars":
            missing.append("JWT_SECRET")
        if not self.ENCRYPTION_KEY:
            missing.append("ENCRYPTION_KEY")
        if not self.COOKIE_SECURE:
            missing.append("COOKIE_SECURE=true")
        if missing:
            raise ValueError(f"Production security settings are missing: {', '.join(missing)}")
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def github_app_install_url(self) -> str:
        return f"https://github.com/apps/{self.GITHUB_APP_SLUG}/installations/new"

    @property
    def github_app_private_key_pem(self) -> str:
        key = self.GITHUB_APP_PRIVATE_KEY
        return key.replace("\\n", "\n") if key else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
