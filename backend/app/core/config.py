import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings:
    app_name: str = os.getenv("APP_NAME", "SentinelAI")
    # JWT_SECRET_KEY preserves compatibility with the former standalone RAG
    # environment during the repository-layout migration.
    secret_key: str = (
        os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or "dev-secret-key"
    )
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    postgres_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/sentinelaidb_college",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5174,http://127.0.0.1:5174",
    )
    env: str = os.getenv("ENV", "development")
    redis_rate_limit_window_seconds: int = int(os.getenv("REDIS_RATE_LIMIT_WINDOW_SECONDS", 60))
    redis_rate_limit_max_requests: int = int(os.getenv("REDIS_RATE_LIMIT_MAX_REQUESTS", 10))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_timeout_seconds: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", 30))
    openai_retry_count: int = int(os.getenv("OPENAI_RETRY_COUNT", 1))
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_timeout_seconds: int = int(os.getenv("GROQ_TIMEOUT_SECONDS", 30))
    groq_retry_count: int = int(os.getenv("GROQ_RETRY_COUNT", 2))
    groq_max_completion_tokens: int = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", 1200))

    def __init__(self) -> None:
        if not self.postgres_url.startswith("postgresql+psycopg://"):
            raise RuntimeError("DATABASE_URL must use the PostgreSQL psycopg URL format")

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def assistant_provider(self) -> str:
        if self.openai_api_key:
            return "openai"
        if self.groq_api_key:
            return "groq"
        return "unconfigured"

    @property
    def assistant_model(self) -> str | None:
        if self.openai_api_key:
            return self.openai_model
        if self.groq_api_key:
            return self.groq_model
        return None


settings = Settings()
