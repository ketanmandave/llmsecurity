"""Lazy local cross-encoder reranking for authorized retrieval candidates."""

import asyncio
from functools import lru_cache
from pathlib import Path

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.config import get_settings
from app.retrieval.retriever import RetrievedChunk


class RerankerError(RuntimeError):
    """Raised when the configured reranker cannot score candidates."""


class LocalReranker:
    def __init__(
        self, model_name: str, batch_size: int, cache_dir: Path | None = None
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self._model: TextCrossEncoder | None = None
        self._lock = asyncio.Lock()

    def _get_model(self) -> TextCrossEncoder:
        if self._model is None:
            self._model = TextCrossEncoder(
                model_name=self.model_name,
                cache_dir=str(self.cache_dir) if self.cache_dir else None,
            )
        return self._model

    def _rerank_sync(self, query: str, chunks: list[RetrievedChunk]) -> list[float]:
        documents = [
            f"Document title: {chunk.document_name}\n{chunk.content}" for chunk in chunks
        ]
        try:
            scores = [
                float(score)
                for score in self._get_model().rerank(
                    query,
                    documents,
                    batch_size=self.batch_size,
                )
            ]
        except Exception as exc:
            raise RerankerError("Local reranker failed") from exc
        if len(scores) != len(chunks):
            raise RerankerError("Reranker returned an unexpected score count")
        return scores

    async def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[float]:
        if not chunks:
            return []
        async with self._lock:
            return await asyncio.to_thread(self._rerank_sync, query, chunks)


@lru_cache
def get_reranker() -> LocalReranker:
    settings = get_settings()
    return LocalReranker(
        model_name=settings.reranker_model_name,
        batch_size=settings.reranker_batch_size,
        cache_dir=settings.model_cache_directory,
    )
