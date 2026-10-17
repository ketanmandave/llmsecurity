"""Authorized retrieval and grounded-generation orchestration."""

from dataclasses import dataclass
from typing import Protocol
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.auth.jwt import Principal
from app.rag.config import Settings
from app.rag.generation.citations import Citation, validate_and_build_citations
from app.rag.generation.llm import GeneratedAnswer
from app.rag.generation.prompts import build_generation_messages
from app.rag.models.enums import PolicyDecision
from app.rag.retrieval.ranking import CandidateReranker, rank_candidates
from app.rag.retrieval.retriever import (
    retrieve_authorized_chunks,
    validate_authorized_document_scope,
)
from app.rag.security.context_guard import inspect_retrieved_chunks
from app.rag.security.output_guard import inspect_model_output
from app.rag.security.policy import combine_decisions


INSUFFICIENT_CONTEXT_ANSWER = (
    "I could not find enough information in the documents available to your account "
    "to answer this question."
)


class QueryEmbedder(Protocol):
    """Embedding dependency accepted by query orchestration and tests."""

    async def embed_query(self, query: str) -> list[float]:
        """Convert a sanitized user question into a retrieval vector."""

        ...


class AnswerGenerator(Protocol):
    """LLM dependency that converts grounded prompt messages into an answer."""

    model: str

    async def generate(self, messages: list[dict[str, str]]) -> GeneratedAnswer:
        """Generate a schema-valid answer from trusted prompt messages."""

        ...


@dataclass(frozen=True, slots=True)
class GroundedQueryResult:
    """Internal query result returned to the API before response serialization."""

    answer: str
    grounded: bool
    citations: list[Citation]
    decision: PolicyDecision
    retrieved_document_ids: list[uuid.UUID]
    retrieved_chunk_count: int
    dropped_chunk_count: int
    redacted_chunk_count: int
    context_findings: tuple[str, ...]
    output_findings: tuple[str, ...]


async def answer_authorized_query(
    session: AsyncSession,
    principal: Principal,
    question: str,
    top_k: int,
    settings: Settings,
    embedder: QueryEmbedder,
    generator: AnswerGenerator,
    reranker: CandidateReranker,
    document_ids: list[uuid.UUID] | None = None,
) -> GroundedQueryResult:
    """Retrieve authorized evidence and produce a citation-validated answer."""

    await validate_authorized_document_scope(
        session,
        principal.role_ids,
        document_ids,
    )
    query_embedding = await embedder.embed_query(question)
    candidate_k = min(
        max(settings.retrieval_candidate_k, top_k * 3),
        settings.retrieval_max_candidates,
    )
    candidates = await retrieve_authorized_chunks(
        session=session,
        query_embedding=query_embedding,
        verified_role_ids=principal.role_ids,
        top_k=candidate_k,
        minimum_score=settings.retrieval_min_score,
        query_text=question,
        document_ids=document_ids,
    )
    chunks = await rank_candidates(
        question=question,
        candidates=candidates,
        top_k=top_k,
        settings=settings,
        reranker=reranker,
    )
    document_ids = list(dict.fromkeys(chunk.document_id for chunk in chunks))
    if not chunks:
        return GroundedQueryResult(
            answer=INSUFFICIENT_CONTEXT_ANSWER,
            grounded=False,
            citations=[],
            decision=PolicyDecision.ALLOW,
            retrieved_document_ids=[],
            retrieved_chunk_count=0,
            dropped_chunk_count=0,
            redacted_chunk_count=0,
            context_findings=(),
            output_findings=(),
        )

    guarded_context = inspect_retrieved_chunks(chunks)
    if not guarded_context.chunks:
        return GroundedQueryResult(
            answer=INSUFFICIENT_CONTEXT_ANSWER,
            grounded=False,
            citations=[],
            decision=PolicyDecision.BLOCK,
            retrieved_document_ids=document_ids,
            retrieved_chunk_count=len(chunks),
            dropped_chunk_count=guarded_context.dropped_chunks,
            redacted_chunk_count=guarded_context.redacted_chunks,
            context_findings=guarded_context.findings,
            output_findings=(),
        )

    messages, source_map = build_generation_messages(
        question=question,
        chunks=guarded_context.chunks,
        max_context_characters=settings.rag_max_context_characters,
    )
    generated = await generator.generate(messages)
    if not generated.grounded:
        return GroundedQueryResult(
            answer=INSUFFICIENT_CONTEXT_ANSWER,
            grounded=False,
            citations=[],
            decision=(
                PolicyDecision.MODIFY
                if guarded_context.dropped_chunks or guarded_context.redacted_chunks
                else PolicyDecision.ALLOW
            ),
            retrieved_document_ids=document_ids,
            retrieved_chunk_count=len(chunks),
            dropped_chunk_count=guarded_context.dropped_chunks,
            redacted_chunk_count=guarded_context.redacted_chunks,
            context_findings=guarded_context.findings,
            output_findings=(),
        )
    citations = validate_and_build_citations(generated, source_map)
    guarded_output = inspect_model_output(generated.answer)
    context_decision = (
        PolicyDecision.MODIFY
        if guarded_context.dropped_chunks or guarded_context.redacted_chunks
        else PolicyDecision.ALLOW
    )
    return GroundedQueryResult(
        answer=guarded_output.text,
        grounded=True,
        citations=citations,
        decision=combine_decisions(context_decision, guarded_output.decision),
        retrieved_document_ids=document_ids,
        retrieved_chunk_count=len(chunks),
        dropped_chunk_count=guarded_context.dropped_chunks,
        redacted_chunk_count=guarded_context.redacted_chunks,
        context_findings=guarded_context.findings,
        output_findings=guarded_output.findings,
    )
