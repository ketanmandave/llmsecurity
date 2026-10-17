"""Hybrid score fusion and dynamic relevance filtering."""

import math
from dataclasses import replace
from typing import Protocol

from app.rag.config import Settings
from app.rag.retrieval.retriever import RetrievedChunk


class CandidateReranker(Protocol):
    """Interface for an optional second-stage candidate scorer."""

    async def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[float]:
        """Return one relevance score for each candidate in the same order."""

        ...


def _normalize(values: list[float]) -> list[float]:
    """Scale a score list into the zero-to-one range without changing order."""

    if not values:
        return []
    maximum = max(values)
    if maximum <= 0:
        return [0.0] * len(values)
    return [max(value, 0.0) / maximum for value in values]


def _sigmoid(value: float) -> float:
    """Convert an unbounded cross-encoder score into a zero-to-one value."""

    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


async def rank_candidates(
    question: str,
    candidates: list[RetrievedChunk],
    top_k: int,
    settings: Settings,
    reranker: CandidateReranker,
) -> list[RetrievedChunk]:
    """Fuse vector, lexical, title, and cross-encoder scores, then prune noise."""

    if not candidates:
        return []
    lexical = _normalize([chunk.lexical_score for chunk in candidates])
    title = _normalize([chunk.title_score for chunk in candidates])
    if settings.reranker_enabled:
        raw_reranker = await reranker.rerank(question, candidates)
        reranker_scores: list[float | None] = [_sigmoid(score) for score in raw_reranker]
    else:
        reranker_scores = [None] * len(candidates)

    ranked: list[RetrievedChunk] = []
    for index, chunk in enumerate(candidates):
        vector_score = chunk.vector_score if chunk.vector_score is not None else chunk.score
        if reranker_scores[index] is None:
            final_score = 0.65 * vector_score + 0.22 * lexical[index] + 0.13 * title[index]
        else:
            final_score = (
                0.45 * reranker_scores[index]
                + 0.35 * vector_score
                + 0.12 * lexical[index]
                + 0.08 * title[index]
            )
        ranked.append(
            replace(
                chunk,
                score=max(0.0, min(float(final_score), 1.0)),
                vector_score=float(vector_score),
                lexical_score=lexical[index],
                title_score=title[index],
                reranker_score=reranker_scores[index],
            )
        )

    ranked.sort(key=lambda chunk: chunk.score, reverse=True)
    best_score = ranked[0].score
    cutoff = max(
        settings.retrieval_final_min_score,
        best_score - settings.retrieval_relative_score_margin,
    )
    return [chunk for chunk in ranked if chunk.score >= cutoff][:top_k]
