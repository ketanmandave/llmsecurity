"""Document persistence, file validation, and permission management."""

import asyncio
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

from app.models.role import Role
from app.rag.api.schemas.documents import DocumentResponse, RoleOption
from app.rag.auth.jwt import normalize_role_slug
from app.rag.config import Settings
from app.rag.ingestion.parser import PdfParsingError, extract_pdf_pages, validate_pdf_structure
from app.rag.models import (
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
    """Validated server-side PDF location and immutable file metadata."""

    storage_key: str
    original_filename: str
    mime_type: str
    checksum_sha256: str
    size_bytes: int
    absolute_path: Path


def parse_allowed_role_ids(raw_roles: str) -> list[int]:
    """Parse role IDs from a JSON array or comma-separated multipart field."""

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
        role_ids = [int(value) for value in values]
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="allowed_roles must contain SentinelAI role IDs",
        ) from exc

    if any(role_id < 1 for role_id in role_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="allowed_roles must contain positive role IDs",
        )
    if len(role_ids) != len(set(role_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="allowed_roles must not contain duplicates",
        )
    return role_ids


async def validate_role_ids(session: AsyncSession, role_ids: list[int]) -> None:
    """Reject ACL identifiers that do not exist in SentinelAI's role table."""

    existing = set(
        (
            await session.scalars(
                select(Role.id).where(Role.id.in_(set(role_ids)))
            )
        ).all()
    )
    if existing != set(role_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="One or more allowed role IDs do not exist",
        )


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
    if upload.content_type and upload.content_type not in {
        "application/pdf",
        "application/octet-stream",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded content type must be application/pdf",
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
        total_pages=document.total_pages,
        processing_error=document.processing_error,
        metadata=document.document_metadata,
        allowed_roles=[
            RoleOption(
                id=entry.role.id,
                name=entry.role.name,
                slug=normalize_role_slug(entry.role.name),
            )
            for entry in sorted(document.roles, key=lambda item: item.role.name.casefold())
        ],
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


async def create_document(
    session: AsyncSession,
    settings: Settings,
    upload: UploadFile,
    name: str,
    classification: Classification,
    role_ids: list[int],
    uploaded_by: str,
) -> Document:
    """Validate native PDF text, detect duplicates, and create its ACL record."""

    await validate_role_ids(session, role_ids)
    document_id = uuid.uuid4()
    stored = await store_pdf(upload, document_id, settings)
    try:
        total_pages = await asyncio.to_thread(
            validate_pdf_structure,
            stored.absolute_path,
            settings.max_pdf_pages,
        )
        # Reject scanned/image-only files before creating a database record or
        # scheduling background work. This service intentionally supports only
        # PDFs that contain a native, extractable text layer.
        await asyncio.to_thread(
            extract_pdf_pages,
            stored.absolute_path,
            settings.max_pdf_pages,
        )
        duplicate_result = await session.scalars(
            select(Document.id).where(Document.checksum_sha256 == stored.checksum_sha256)
        )
        duplicate_ids = list(duplicate_result.all())
        if duplicate_ids and settings.duplicate_document_policy == "reject":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This PDF has already been uploaded",
            )
    except PdfParsingError as exc:
        stored.absolute_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception:
        stored.absolute_path.unlink(missing_ok=True)
        raise
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
        total_pages=total_pages,
        document_metadata=(
            {"duplicate_of": [str(value) for value in duplicate_ids]}
            if duplicate_ids and settings.duplicate_document_policy == "warn"
            else {}
        ),
        roles=[DocumentRole(role_id=role_id) for role_id in role_ids],
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
    """Load one document and its roles or raise a consistent HTTP 404 error."""

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
    """Return a page of documents plus the unpaginated total count."""

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
    role_ids: list[int],
) -> Document:
    """Replace all role grants for a document within the current transaction."""

    await validate_role_ids(session, role_ids)
    document.roles = [DocumentRole(role_id=role_id) for role_id in role_ids]
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
            Chunk.content_type == "text",
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
    """Count generated chunks and recorded findings for status polling."""

    chunks_result = await session.execute(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    )
    findings_result = await session.execute(
        select(func.count())
        .select_from(SecurityFinding)
        .where(SecurityFinding.document_id == document_id)
    )
    return chunks_result.scalar_one(), findings_result.scalar_one()
