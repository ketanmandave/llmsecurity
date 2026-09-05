"""Final role-aware RAG answer endpoint."""

import uuid
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.generation import CitationResponse, RAGQueryRequest, RAGQueryResponse
from app.auth.jwt import Principal, get_current_principal
from app.config import Settings, get_settings
from app.database import get_db_session
from app.generation.llm import (
    GroqLLMService,
    LLMConfigurationError,
    LLMGenerationError,
    get_llm_service,
)
from app.models.enums import PolicyDecision
from app.retrieval.embedder import LocalEmbeddingService, get_embedding_service
from app.retrieval.reranker import LocalReranker, RerankerError, get_reranker
from app.retrieval.retriever import DocumentScopeError
from app.security.input_guard import inspect_user_input
from app.security.policy import combine_decisions
from app.security.rate_limit import (
    RateLimiter,
    RateLimitExceeded,
    RateLimitUnavailable,
    get_rate_limiter,
)
from app.services.audit_service import text_sha256, write_audit_event
from app.services.query_service import answer_authorized_query


router = APIRouter(prefix="/v1", tags=["rag"])


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedder: Annotated[LocalEmbeddingService, Depends(get_embedding_service)],
    reranker: Annotated[LocalReranker, Depends(get_reranker)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> RAGQueryResponse:
    """Generate an answer using only chunks authorized for the caller's roles."""

    request_id = uuid.uuid4()
    started_at = perf_counter()
    question_hash = text_sha256(request.question)
    try:
        await rate_limiter.check(principal.user_id)
    except RateLimitExceeded as exc:
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "rate_limit_exceeded",
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except RateLimitUnavailable as exc:
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "rate_limit_unavailable",
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security rate-limit service is unavailable",
        ) from exc

    input_guard = inspect_user_input(request.question)
    if input_guard.decision is PolicyDecision.BLOCK or not input_guard.text.strip():
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "input_security_policy",
                "findings": list(input_guard.findings),
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request blocked by input security policy",
        )

    try:
        generator: GroqLLMService = get_llm_service()
        result = await answer_authorized_query(
            session=session,
            principal=principal,
            question=input_guard.text,
            top_k=min(
                request.top_k or settings.retrieval_default_top_k,
                settings.retrieval_max_top_k,
            ),
            settings=settings,
            embedder=embedder,
            generator=generator,
            reranker=reranker,
            document_ids=request.document_ids,
        )
    except LLMConfigurationError as exc:
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "llm_not_configured",
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is not configured",
        ) from exc
    except LLMGenerationError as exc:
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "llm_generation_failed",
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM service could not produce a valid grounded response",
        ) from exc
    except RerankerError as exc:
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "reranker_unavailable",
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval reranker is unavailable",
        ) from exc
    except DocumentScopeError as exc:
        await write_audit_event(
            request_id=request_id,
            principal=principal,
            action="rag_query",
            decision=PolicyDecision.BLOCK,
            document_ids=[],
            details={
                "reason": "invalid_document_scope",
                "question_sha256": question_hash,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    final_decision = combine_decisions(input_guard.decision, result.decision)
    await write_audit_event(
        request_id=request_id,
        principal=principal,
        action="rag_query",
        decision=final_decision,
        document_ids=result.retrieved_document_ids,
        details={
            "question_sha256": question_hash,
            "input_findings": list(input_guard.findings),
            "context_findings": list(result.context_findings),
            "output_findings": list(result.output_findings),
            "retrieved_chunks": result.retrieved_chunk_count,
            "dropped_chunks": result.dropped_chunk_count,
            "redacted_chunks": result.redacted_chunk_count,
            "citation_count": len(result.citations),
            "grounded": result.grounded,
            "latency_ms": round((perf_counter() - started_at) * 1000, 2),
            "conversation_id_sha256": (
                text_sha256(request.conversation_id)
                if request.conversation_id is not None
                else None
            ),
        },
    )

    return RAGQueryResponse(
        request_id=request_id,
        answer=result.answer,
        grounded=result.grounded,
        sources=[
            CitationResponse(
                source_id=citation.source_id,
                chunk_id=citation.chunk_id,
                document_id=citation.document_id,
                document_name=citation.document_name,
                page_number=citation.page_number,
            )
            for citation in result.citations
        ],
        model=settings.groq_model,
    )
