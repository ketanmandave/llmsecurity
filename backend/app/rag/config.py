"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# This is part of the persisted database schema. Changing the embedding model to
# one with a different output size requires a database migration and re-indexing.
EMBEDDING_DIMENSION = 384


class Settings(BaseSettings):
    """Runtime settings for the secure RAG service."""

    app_name: str = "Secure Role-Aware RAG"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://secure_rag:secure_rag@localhost:5432/secure_rag"
    )
    upload_directory: Path = Path("uploads")
    max_upload_size_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 500
    duplicate_document_policy: str = "warn"
    chunk_size_words: int = 450
    chunk_overlap_words: int = 75
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_batch_size: int = 32
    model_cache_directory: Path = Path(".model_cache")
    retrieval_default_top_k: int = 5
    retrieval_max_top_k: int = 20
    retrieval_min_score: float = 0.2
    retrieval_candidate_k: int = 20
    retrieval_max_candidates: int = 50
    retrieval_final_min_score: float = 0.35
    retrieval_relative_score_margin: float = 0.12
    reranker_enabled: bool = True
    reranker_model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    reranker_batch_size: int = 16
    rag_max_context_characters: int = 24000
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_max_completion_tokens: int = 1200
    groq_timeout_seconds: float = 30.0
    redis_url: str = "redis://localhost:6380/0"
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    cors_allowed_origins: list[str] = Field(default_factory=list)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def reject_default_secret_outside_development(self) -> "Settings":
        """Validate cross-field security, retrieval, and model configuration."""

        if self.chunk_overlap_words >= self.chunk_size_words:
            raise ValueError("CHUNK_OVERLAP_WORDS must be smaller than CHUNK_SIZE_WORDS")
        if self.duplicate_document_policy not in {"allow", "warn", "reject"}:
            raise ValueError("DUPLICATE_DOCUMENT_POLICY must be allow, warn, or reject")
        if self.embedding_batch_size < 1:
            raise ValueError("EMBEDDING_BATCH_SIZE must be positive")
        if not 1 <= self.retrieval_default_top_k <= self.retrieval_max_top_k:
            raise ValueError("RETRIEVAL_DEFAULT_TOP_K must be within the maximum")
        if not -1 <= self.retrieval_min_score <= 1:
            raise ValueError("RETRIEVAL_MIN_SCORE must be between -1 and 1")
        if not 1 <= self.retrieval_candidate_k <= self.retrieval_max_candidates:
            raise ValueError("RETRIEVAL_CANDIDATE_K must be within the candidate maximum")
        if self.retrieval_max_candidates > 100:
            raise ValueError("RETRIEVAL_MAX_CANDIDATES cannot exceed 100")
        if not 0 <= self.retrieval_final_min_score <= 1:
            raise ValueError("RETRIEVAL_FINAL_MIN_SCORE must be between 0 and 1")
        if not 0 <= self.retrieval_relative_score_margin <= 1:
            raise ValueError("RETRIEVAL_RELATIVE_SCORE_MARGIN must be between 0 and 1")
        if self.reranker_batch_size < 1:
            raise ValueError("RERANKER_BATCH_SIZE must be positive")
        if self.rag_max_context_characters < 1000:
            raise ValueError("RAG_MAX_CONTEXT_CHARACTERS must be at least 1000")
        if self.groq_model != "openai/gpt-oss-120b":
            raise ValueError("GROQ_MODEL must be openai/gpt-oss-120b for this project")
        if self.groq_max_completion_tokens < 1:
            raise ValueError("GROQ_MAX_COMPLETION_TOKENS must be positive")
        if self.groq_timeout_seconds <= 0:
            raise ValueError("GROQ_TIMEOUT_SECONDS must be positive")
        if self.rate_limit_requests < 1 or self.rate_limit_window_seconds < 1:
            raise ValueError("Rate-limit values must be positive")
        if (
            self.environment.lower() != "development"
            and "*" in self.cors_allowed_origins
        ):
            raise ValueError("Wildcard CORS origins are not allowed outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object per process."""

    return Settings()
