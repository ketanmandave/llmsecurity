"""Role-filtered vector retrieval enforced inside the database query."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import Float, cast, exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.models import Chunk, Document, DocumentRole, DocumentStatus, SecurityStatus


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Authorized database candidate plus provenance and relevance signals."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int | None
    content: str
    score: float
    content_type: str = "text"
    source_type: str = "pymupdf"
    extraction_metadata: dict | None = None
    vector_score: float | None = None
    lexical_score: float = 0.0
    title_score: float = 0.0
    reranker_score: float | None = None


class DocumentScopeError(ValueError):
    """Raised when a requested document is unavailable to the caller."""


QUERY_STOP_WORDS = frozenset(
    {
        "a", "an", "and", "are", "for", "from", "given", "in", "is", "of",
        "on", "the", "to", "what", "which", "with",
    }
)


def _tsquery_text(query: str) -> str | None:
    """Build a safe OR query from meaningful alphanumeric terms."""

    terms = [
        term
        for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 1 and term not in QUERY_STOP_WORDS
    ]
    unique_terms = list(dict.fromkeys(terms))[:20]
    return " | ".join(unique_terms) if unique_terms else None


async def validate_authorized_document_scope(
    session: AsyncSession,
    verified_role_ids: frozenset[int],
    document_ids: list[uuid.UUID] | None,
) -> None:
    """Reject invalid, inactive, or unauthorized explicit document scopes."""

    if document_ids is None:
        return
    requested_ids = set(document_ids)
    role_authorization = exists(
        select(DocumentRole.document_id).where(
            DocumentRole.document_id == Document.id,
            DocumentRole.role_id.in_(list(verified_role_ids)),
        )
    )
    result = await session.scalars(
        select(Document.id).where(
            Document.id.in_(requested_ids),
            Document.status == DocumentStatus.ACTIVE,
            role_authorization,
        )
    )
    if set(result.all()) != requested_ids:
        raise DocumentScopeError(
            "One or more requested documents were not found or are not accessible"
        )


async def retrieve_authorized_chunks(
    session: AsyncSession,
    query_embedding: list[float],
    verified_role_ids: frozenset[int],
    top_k: int,
    minimum_score: float,
    query_text: str = "",
    document_ids: list[uuid.UUID] | None = None,
) -> list[RetrievedChunk]:
    """Return authorized vector candidates with PostgreSQL lexical signals."""

    if not verified_role_ids:
        return []

    distance = Chunk.embedding.cosine_distance(query_embedding)
    score = (1 - distance).label("score")
    tsquery_text = _tsquery_text(query_text)
    if tsquery_text:
        content_query = func.to_tsquery("english", tsquery_text)
        title_query = func.to_tsquery("simple", tsquery_text)
        lexical_score = cast(
            func.ts_rank_cd(func.to_tsvector("english", Chunk.content), content_query),
            Float,
        ).label("lexical_score")
        title_score = cast(
            func.ts_rank_cd(func.to_tsvector("simple", Document.name), title_query),
            Float,
        ).label("title_score")
    else:
        lexical_score = literal(0.0, type_=Float).label("lexical_score")
        title_score = literal(0.0, type_=Float).label("title_score")
    role_authorization = exists(
        select(DocumentRole.document_id).where(
            DocumentRole.document_id == Document.id,
            DocumentRole.role_id.in_(list(verified_role_ids)),
        )
    )

    filters = [
        Document.status == DocumentStatus.ACTIVE,
        Chunk.security_status == SecurityStatus.APPROVED,
        Chunk.content_type == "text",
        Chunk.embedding.is_not(None),
        role_authorization,
        distance <= 1 - minimum_score,
    ]
    if document_ids is not None:
        filters.append(Document.id.in_(document_ids))

    statement = (
        select(
            Chunk.id.label("chunk_id"),
            Document.id.label("document_id"),
            Document.name.label("document_name"),
            Chunk.page_number,
            Chunk.content,
            Chunk.content_type,
            Chunk.source_type,
            Chunk.extraction_metadata,
            score,
            lexical_score,
            title_score,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(*filters)
        .order_by(distance)
        .limit(top_k)
    )
    rows = (await session.execute(statement)).all()
    return [
        RetrievedChunk(
            chunk_id=row.chunk_id,
            document_id=row.document_id,
            document_name=row.document_name,
            page_number=row.page_number,
            content=row.content,
            score=float(row.score),
            content_type=row.content_type,
            source_type=row.source_type,
            extraction_metadata=row.extraction_metadata,
            vector_score=float(row.score),
            lexical_score=float(row.lexical_score),
            title_score=float(row.title_score),
        )
        for row in rows
    ]
