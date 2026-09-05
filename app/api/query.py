"""Role-aware retrieval routes."""

import uuid
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunkResponse,
)
from app.auth.jwt import Principal, get_current_principal
from app.config import Settings, get_settings
from app.database import get_db_session
from app.models.enums import PolicyDecision
from app.retrieval.embedder import LocalEmbeddingService, get_embedding_service
from app.retrieval.ranking import rank_candidates
from app.retrieval.reranker import LocalReranker, RerankerError, get_reranker
from app.retrieval.retriever import (
    DocumentScopeError,
    retrieve_authorized_chunks,
    validate_authorized_document_scope,
)
from app.security.context_guard import inspect_retrieved_chunks
from app.security.input_guard import inspect_user_input
from app.security.policy import combine_decisions
from app.security.rate_limit import (
    RateLimiter,
    RateLimitExceeded,
    RateLimitUnavailable,
    get_rate_limiter,
)
from app.services.audit_service import text_sha256, write_audit_event


router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search_authorized_documents(
    request: RetrievalRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[LocalEmbeddingService, Depends(get_embedding_service)],
    reranker: Annotated[LocalReranker, Depends(get_reranker)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> RetrievalResponse:
    """Search only chunks accessible to the authenticated user's roles."""

    request_id = uuid.uuid4()
    started_at = perf_counter()
    question_hash = text_sha256(request.question)
    try:
        await rate_limiter.check(principal.user_id)
    except RateLimitExceeded as exc:
        await write_audit_event(
            request_id,
            principal,
            "retrieval_search",
            PolicyDecision.BLOCK,
            [],
            {"reason": "rate_limit_exceeded", "question_sha256": question_hash},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except RateLimitUnavailable as exc:
        await write_audit_event(
            request_id,
            principal,
            "retrieval_search",
            PolicyDecision.BLOCK,
            [],
            {"reason": "rate_limit_unavailable", "question_sha256": question_hash},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security rate-limit service is unavailable",
        ) from exc

    input_guard = inspect_user_input(request.question)
    if input_guard.decision is PolicyDecision.BLOCK or not input_guard.text.strip():
        await write_audit_event(
            request_id,
            principal,
            "retrieval_search",
            PolicyDecision.BLOCK,
            [],
            {
                "reason": "input_security_policy",
                "findings": list(input_guard.findings),
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request blocked by input security policy",
        )

    top_k = request.top_k or settings.retrieval_default_top_k
    top_k = min(top_k, settings.retrieval_max_top_k)
    try:
        await validate_authorized_document_scope(
            session,
            principal.roles,
            request.document_ids,
        )
    except DocumentScopeError as exc:
        await write_audit_event(
            request_id,
            principal,
            "retrieval_search",
            PolicyDecision.BLOCK,
            [],
            {"reason": "invalid_document_scope", "question_sha256": question_hash},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    embedding = await embedder.embed_query(input_guard.text)
    candidate_k = min(
        max(settings.retrieval_candidate_k, top_k * 3),
        settings.retrieval_max_candidates,
    )
    candidates = await retrieve_authorized_chunks(
        session=session,
        query_embedding=embedding,
        verified_roles=principal.roles,
        top_k=candidate_k,
        minimum_score=settings.retrieval_min_score,
        query_text=input_guard.text,
        document_ids=request.document_ids,
    )
    try:
        chunks = await rank_candidates(
            question=input_guard.text,
            candidates=candidates,
            top_k=top_k,
            settings=settings,
            reranker=reranker,
        )
    except RerankerError as exc:
        await write_audit_event(
            request_id,
            principal,
            "retrieval_search",
            PolicyDecision.BLOCK,
            [],
            {"reason": "reranker_unavailable", "question_sha256": question_hash},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval reranker is unavailable",
        ) from exc
    guarded_context = inspect_retrieved_chunks(chunks)
    context_decision = (
        PolicyDecision.MODIFY
        if guarded_context.dropped_chunks or guarded_context.redacted_chunks
        else PolicyDecision.ALLOW
    )
    decision = combine_decisions(input_guard.decision, context_decision)
    document_ids = list(
        dict.fromkeys(chunk.document_id for chunk in guarded_context.chunks)
    )
    await write_audit_event(
        request_id,
        principal,
        "retrieval_search",
        decision,
        document_ids,
        {
            "question_sha256": question_hash,
            "input_findings": list(input_guard.findings),
            "context_findings": list(guarded_context.findings),
            "candidate_chunks": len(candidates),
            "retrieved_chunks": len(chunks),
            "returned_chunks": len(guarded_context.chunks),
            "dropped_chunks": guarded_context.dropped_chunks,
            "redacted_chunks": guarded_context.redacted_chunks,
            "latency_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return RetrievalResponse(
        request_id=request_id,
        results=[
            RetrievedChunkResponse(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                content=chunk.content,
                score=chunk.score,
                vector_score=(
                    chunk.vector_score if chunk.vector_score is not None else 0.0
                ),
                lexical_score=chunk.lexical_score,
                title_score=chunk.title_score,
                reranker_score=chunk.reranker_score,
            )
            for chunk in guarded_context.chunks
        ],
    )
