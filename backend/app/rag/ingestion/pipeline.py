"""Document-ingestion workflow orchestration."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.rag.config import Settings, get_settings
from app.rag.database import AsyncSessionFactory
from app.rag.ingestion.chunker import chunk_pages
from app.rag.ingestion.parser import extract_pdf_pages
from app.rag.ingestion.scanner import ScanFinding, scan_and_redact_pages
from app.rag.models import (
    Chunk,
    Document,
    DocumentStatus,
    FindingStatus,
    SecurityFinding,
    SecurityStatus,
    Severity,
)
from app.rag.retrieval.embedder import get_embedding_service

logger = logging.getLogger(__name__)

class Embedder(Protocol):
    """Minimal embedding interface accepted by the ingestion orchestrator."""

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Convert chunk text into database-compatible vectors."""

        ...

def resolve_document_path(settings: Settings, storage_key: str) -> Path:
    """Resolve a storage key while preventing traversal outside the upload root."""

    root = settings.upload_directory.resolve()
    path = (root / storage_key).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Document storage key resolves outside the upload directory")
    return path


def finding_model(document_id: uuid.UUID, finding: ScanFinding) -> SecurityFinding:
    """Convert an in-memory scanner finding into its persisted ORM record."""

    return SecurityFinding(
        document_id=document_id,
        category=finding.category,
        severity=finding.severity,
        confidence=finding.confidence,
        status=FindingStatus.OPEN,
        evidence_hash=finding.evidence_hash,
        description=finding.description,
        details={
            "page_number": finding.page_number,
            "content_type": finding.content_type,
            "source_type": finding.source_type,
        },
    )


async def process_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    settings: Settings,
    embedder: Embedder,
) -> DocumentStatus:
    """Parse, scan, chunk, embed, and publish one uploaded document."""

    result = await session.execute(
        select(Document)
        .options(selectinload(Document.roles))
        .where(Document.id == document_id)
        .with_for_update()
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise ValueError("Document no longer exists")
    if document.status == DocumentStatus.INACTIVE:
        return document.status

    document.status = DocumentStatus.PROCESSING
    await session.execute(delete(Chunk).where(Chunk.document_id == document_id))
    await session.execute(
        delete(SecurityFinding).where(SecurityFinding.document_id == document_id)
    )

    path = resolve_document_path(settings, document.storage_key)
    pages = await asyncio.to_thread(
        extract_pdf_pages,
        path,
        settings.max_pdf_pages,
    )
    document.processing_error = None
    document.document_metadata = {
        **document.document_metadata,
        "extraction_mode": "native_text_only",
        "extraction_counts": {"text": len(pages)},
        "pages_with_text": [page.page_number for page in pages],
    }
    logger.info(
        "Document extraction finished",
        extra={
            "document_id": str(document_id),
            "total_pages": document.total_pages,
            "pages_with_text": len(pages),
        },
    )
    scan = scan_and_redact_pages(pages)
    session.add_all([finding_model(document_id, finding) for finding in scan.findings])

    if scan.should_quarantine:
        document.status = DocumentStatus.QUARANTINED
        document.processing_error = "Document quarantined by content security policy"
        logger.warning(
            "Document quarantined",
            extra={"document_id": str(document_id), "finding_count": len(scan.findings)},
        )
        await session.flush()
        return document.status

    text_chunks = chunk_pages(
        scan.sanitized_pages,
        chunk_size_words=settings.chunk_size_words,
        overlap_words=settings.chunk_overlap_words,
    )
    if not text_chunks:
        raise ValueError("PDF did not produce any searchable chunks")

    vectors = await embedder.embed_documents([chunk.content for chunk in text_chunks])
    session.add_all(
        [
            Chunk(
                document_id=document_id,
                content=chunk.content,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                content_hash=chunk.content_hash,
                content_type=chunk.content_type,
                source_type=chunk.source_type,
                token_count=chunk.token_count,
                extraction_metadata=chunk.metadata or {},
                embedding=vector,
                security_status=SecurityStatus.APPROVED,
            )
            for chunk, vector in zip(text_chunks, vectors, strict=True)
        ]
    )
    document.status = DocumentStatus.ACTIVE
    document.processing_error = None
    logger.info(
        "Document ingestion completed",
        extra={"document_id": str(document_id), "chunk_count": len(text_chunks)},
    )
    await session.flush()
    return document.status


async def _mark_failed(document_id: uuid.UUID) -> None:
    """Persist a safe failure state when a background ingestion job crashes."""

    async with AsyncSessionFactory() as session:
        async with session.begin():
            result = await session.execute(
                select(Document).where(Document.id == document_id).with_for_update()
            )
            document = result.scalar_one_or_none()
            if document is None or document.status == DocumentStatus.INACTIVE:
                return
            document.status = DocumentStatus.FAILED
            document.processing_error = "Document ingestion failed; inspect server logs"
            session.add(
                SecurityFinding(
                    document_id=document_id,
                    category="ingestion_error",
                    severity=Severity.HIGH,
                    confidence=None,
                    status=FindingStatus.OPEN,
                    description="Document ingestion failed; inspect server logs",
                    details={},
                )
            )


async def run_ingestion_job(document_id: uuid.UUID) -> None:
    """Background-task entry point with isolated transaction handling."""

    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                await process_document(
                    session=session,
                    document_id=document_id,
                    settings=get_settings(),
                    embedder=get_embedding_service(),
                )
    except Exception:
        logger.exception("Document ingestion failed", extra={"document_id": str(document_id)})
        await _mark_failed(document_id)
