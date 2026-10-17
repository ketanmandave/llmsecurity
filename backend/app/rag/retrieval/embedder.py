"""Local embedding generation with lazy model initialization."""

import asyncio
from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding

from app.rag.config import EMBEDDING_DIMENSION, get_settings


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be generated in the configured shape."""


class LocalEmbeddingService:
    """Create document and query vectors locally with a lazily loaded ONNX model."""

    def __init__(
        self, model_name: str, batch_size: int, cache_dir: Path | None = None
    ) -> None:
        """Store model settings and create a lock for serialized local inference."""

        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self._model: TextEmbedding | None = None
        self._lock = asyncio.Lock()

    def _get_model(self) -> TextEmbedding:
        """Load the embedding model on first use and reuse it thereafter."""

        if self._model is None:
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=str(self.cache_dir) if self.cache_dir else None,
            )
        return self._model

    def _validate_vectors(
        self, vectors: list[list[float]], expected_count: int
    ) -> list[list[float]]:
        """Ensure the provider returned the expected count and vector dimension."""

        if len(vectors) != expected_count:
            raise EmbeddingError("Embedding provider returned an unexpected vector count")
        if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
            raise EmbeddingError(
                f"Embedding model must return {EMBEDDING_DIMENSION}-dimensional vectors"
            )
        return vectors

    def _embed_documents_sync(self, texts: list[str]) -> list[list[float]]:
        """Run synchronous passage embedding for document chunks."""

        vectors = [
            vector.tolist()
            for vector in self._get_model().passage_embed(
                texts, batch_size=self.batch_size
            )
        ]
        return self._validate_vectors(vectors, len(texts))

    def _embed_query_sync(self, query: str) -> list[float]:
        """Run synchronous query embedding using the model's query mode."""

        vectors = [vector.tolist() for vector in self._get_model().query_embed(query)]
        return self._validate_vectors(vectors, 1)[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks off the event loop while serializing model access."""

        if not texts:
            return []
        # A cached ONNX model is shared across ingestion jobs; serialize calls so
        # concurrent uploads do not contend for the same inference session.
        async with self._lock:
            return await asyncio.to_thread(self._embed_documents_sync, texts)

    async def embed_query(self, query: str) -> list[float]:
        """Validate and embed a user question off the event loop."""

        if not query.strip():
            raise EmbeddingError("Cannot embed an empty query")
        async with self._lock:
            return await asyncio.to_thread(self._embed_query_sync, query)


@lru_cache
def get_embedding_service() -> LocalEmbeddingService:
    """Return the process-wide embedding service configured for this database."""

    settings = get_settings()
    return LocalEmbeddingService(
        model_name=settings.embedding_model_name,
        batch_size=settings.embedding_batch_size,
        cache_dir=settings.model_cache_directory,
    )
