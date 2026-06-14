"""Typed application settings loaded from environment / .env (12-factor)."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "PrepForge"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] | list[str] = Field(default_factory=list)

    # Security
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    JWT_ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://prepforge:prepforge@localhost:5432/prepforge"
    # Optional read replica for analytics/read-heavy queries (falls back to primary).
    READ_DATABASE_URL: str = ""
    # Connection pool (front a PgBouncer in production; see enterprise scaling doc).
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SEC: int = 1800

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:8000"

    # LLM (used from Phase 3)
    LLM_PROVIDER: Literal["ollama", "openai_compatible", "vllm"] = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    LLM_MODEL: str = "llama3.1"

    # Rate limiting (Redis-backed). Disable when running without Redis.
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120

    # Caching (analytics + hot reads). In-memory by default; Redis-backed in prod.
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 30

    # Observability (Phase 8). Core metrics/tracing are built-in; these gate the
    # production exporters (OpenTelemetry OTLP, Langfuse) which load lazily.
    METRICS_ENABLED: bool = True
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "prepforge-backend"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # File storage (resume uploads). Local disk in dev; S3/MinIO in prod (Phase 9).
    STORAGE_DIR: str = "storage"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_UPLOAD_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".txt")

    # Code execution (coding interview platform).
    # Judge0 is the production sandbox; the local Python runner is for dev/tests
    # ONLY and must be disabled in production (untrusted code must run sandboxed).
    JUDGE0_URL: str = ""
    JUDGE0_KEY: str = ""
    ALLOW_LOCAL_CODE_EXECUTION: bool = True
    CODE_EXEC_TIMEOUT_SEC: int = 8
    MAX_SOURCE_BYTES: int = 64 * 1024  # 64 KB submission cap

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic (psycopg/psycopg2 driver)."""
        return self.DATABASE_URL.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
