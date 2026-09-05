"""Document persistence, file validation, and permission management."""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.documents import DocumentResponse
from app.config import Settings
from app.models import (
    AccessRole,
    Classification,
    Document,
    DocumentRole,
    DocumentStatus,
    Chunk,
    SecurityFinding,
    SecurityStatus,
)


PDF_MAGIC = b"%PDF-"
READ_CHUNK_SIZE = 1024 * 1024
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredUpload:
    storage_key: str
    original_filename: str
    mime_type: str
    checksum_sha256: str
    size_bytes: int
    absolute_path: Path


def parse_allowed_roles(raw_roles: str) -> list[AccessRole]:
    """Parse JSON-array or comma-separated roles from a multipart form field."""

    raw_roles = raw_roles.strip()
    if raw_roles.startswith("["):
        try:
            values = json.loads(raw_roles)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="allowed_roles contains invalid JSON",
            ) from exc
    else:
        values = [value.strip() for value in raw_roles.split(",") if value.strip()]

    if not isinstance(values, list) or not values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="allowed_roles must contain at least one role",
        )

    try:
        roles = [AccessRole(value) for value in values]
    except (ValueError, TypeError) as exc:
        allowed = ", ".join(role.value for role in AccessRole)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown role. Allowed roles: {allowed}",
        ) from exc

    if len(roles) != len(set(roles)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="allowed_roles must not contain duplicates",
        )
    return roles


async def store_pdf(
    upload: UploadFile,
    document_id: uuid.UUID,
    settings: Settings,
) -> StoredUpload:
    """Validate and atomically store a PDF under a generated server-side name."""

    original_filename = Path(upload.filename or "").name
    if not original_filename or Path(original_filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    storage_root = settings.upload_directory.resolve()
    document_directory = (storage_root / "documents").resolve()
    document_directory.mkdir(parents=True, exist_ok=True)
    destination = document_directory / f"{document_id}.pdf"
    temporary = document_directory / f".{document_id}.uploading"

    digest = hashlib.sha256()
    size = 0
    first_chunk = True

    try:
        with temporary.open("xb") as output:
            while chunk := await upload.read(READ_CHUNK_SIZE):
                if first_chunk:
                    if not chunk.startswith(PDF_MAGIC):
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="File content is not a valid PDF",
                        )
                    first_chunk = False

                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="PDF exceeds the configured upload-size limit",
                    )
                digest.update(chunk)
                output.write(chunk)

        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded PDF is empty",
            )
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return StoredUpload(
        storage_key=f"documents/{document_id}.pdf",
        original_filename=original_filename,
        mime_type="application/pdf",
        checksum_sha256=digest.hexdigest(),
        size_bytes=size,
        absolute_path=destination,
    )


def to_document_response(document: Document) -> DocumentResponse:
    """Map an ORM document and its ACL rows to the public response model."""

    return DocumentResponse(
        id=document.id,
        name=document.name,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        checksum_sha256=document.checksum_sha256,
        size_bytes=document.size_bytes,
        classification=document.classification,
        status=document.status,
        uploaded_by=document.uploaded_by,
        allowed_roles=sorted((entry.role for entry in document.roles), key=lambda r: r.value),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


async def create_document(
    session: AsyncSession,
    settings: Settings,
    upload: UploadFile,
    name: str,
    classification: Classification,
    roles: list[AccessRole],
    uploaded_by: str,
) -> Document:
    document_id = uuid.uuid4()
    stored = await store_pdf(upload, document_id, settings)
    document = Document(
        id=document_id,
        name=name.strip(),
        original_filename=stored.original_filename,
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        checksum_sha256=stored.checksum_sha256,
        size_bytes=stored.size_bytes,
        classification=classification,
        status=DocumentStatus.PROCESSING,
        uploaded_by=uploaded_by,
        roles=[DocumentRole(role=role) for role in roles],
    )
    session.add(document)
    try:
        await session.flush()
        await session.refresh(document, attribute_names=["roles"])
    except Exception:
        stored.absolute_path.unlink(missing_ok=True)
        raise
    return document


async def get_document_or_404(
    session: AsyncSession, document_id: uuid.UUID
) -> Document:
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.roles))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


async def list_documents(
    session: AsyncSession, limit: int, offset: int
) -> tuple[list[Document], int]:
    documents_result = await session.execute(
        select(Document)
        .options(selectinload(Document.roles))
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_result = await session.execute(select(func.count()).select_from(Document))
    return list(documents_result.scalars().all()), count_result.scalar_one()


async def replace_document_roles(
    session: AsyncSession,
    document: Document,
    roles: list[AccessRole],
) -> Document:
    document.roles = [DocumentRole(role=role) for role in roles]
    await session.flush()
    return document


async def deactivate_document(session: AsyncSession, document: Document) -> Document:
    """Make a document immediately ineligible for retrieval without deleting it."""

    document.status = DocumentStatus.INACTIVE
    await session.flush()
    return document


async def activate_document(
    session: AsyncSession,
    document: Document,
) -> tuple[Document, bool]:
    """Reactivate existing vectors or mark an unindexed document for processing."""

    if document.status != DocumentStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an inactive document can be activated",
        )
    approved_chunks = await session.scalar(
        select(func.count())
        .select_from(Chunk)
        .where(
            Chunk.document_id == document.id,
            Chunk.security_status == SecurityStatus.APPROVED,
            Chunk.embedding.is_not(None),
        )
    )
    requires_processing = not bool(approved_chunks)
    document.status = (
        DocumentStatus.PROCESSING if requires_processing else DocumentStatus.ACTIVE
    )
    await session.flush()
    return document, requires_processing


async def permanently_delete_document(
    session: AsyncSession,
    document: Document,
    settings: Settings,
) -> bool:
    """Delete a document and all database-owned knowledge, then remove its PDF.

    PostgreSQL cascades remove role rows, chunks/vectors, and security findings.
    The transaction is committed before filesystem cleanup so retrieval cannot
    continue serving a document whose file cleanup happens to fail.
    """

    upload_root = settings.upload_directory.resolve()
    stored_path = (upload_root / document.storage_key).resolve()
    if not stored_path.is_relative_to(upload_root):
        raise ValueError("Document storage key resolves outside the upload directory")

    await session.execute(delete(Document).where(Document.id == document.id))
    await session.commit()

    try:
        stored_path.unlink(missing_ok=True)
    except OSError:
        logger.exception(
            "Database document was deleted but stored PDF cleanup failed",
            extra={"document_id": str(document.id), "storage_key": document.storage_key},
        )
        return False
    return True


async def get_processing_counts(
    session: AsyncSession, document_id: uuid.UUID
) -> tuple[int, int]:
    chunks_result = await session.execute(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    )
    findings_result = await session.execute(
        select(func.count())
        .select_from(SecurityFinding)
        .where(SecurityFinding.document_id == document_id)
    )
    return chunks_result.scalar_one(), findings_result.scalar_one()
