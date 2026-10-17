"""Run the public RAG query workflow for a SentinelAI conversation."""

import uuid

from app.rag.api.rag import query_documents
from app.rag.api.schemas.generation import RAGQueryRequest, RAGQueryResponse
from app.rag.auth.jwt import Principal
from app.rag.config import get_settings
from app.rag.database import AsyncSessionFactory
from app.rag.retrieval.embedder import get_embedding_service
from app.rag.retrieval.reranker import get_reranker
from app.rag.security.rate_limit import get_rate_limiter


async def answer_conversation_question(
    *,
    principal: Principal,
    question: str,
    conversation_id: str,
    request_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None,
) -> RAGQueryResponse:
    """Execute the same secured RAG workflow used by `/api/v1/rag/query`."""

    async with AsyncSessionFactory() as session:
        return await query_documents(
            request=RAGQueryRequest(
                question=question,
                conversation_id=conversation_id,
                document_ids=document_ids,
            ),
            principal=principal,
            session=session,
            settings=get_settings(),
            embedder=get_embedding_service(),
            reranker=get_reranker(),
            rate_limiter=get_rate_limiter(),
            request_id=request_id,
        )
