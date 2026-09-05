"""Document upload and access-management routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.documents import (
    DocumentActivationResponse,
    DocumentDeactivationResponse,
    DocumentListResponse,
    DocumentPermanentDeletionResponse,
    DocumentProcessingStatusResponse,
    DocumentResponse,
    DocumentUploadConfigResponse,
    DocumentUploadResponse,
    RoleAccessUpdate,
)
from app.auth.jwt import Principal
from app.auth.permissions import require_admin
from app.config import Settings, get_settings
from app.database import get_db_session
from app.models.enums import AccessRole, Classification, DocumentStatus
from app.ingestion.pipeline import run_ingestion_job
from app.services.document_service import (
    activate_document,
    create_document,
    deactivate_document,
    get_document_or_404,
    get_processing_counts,
    list_documents,
    parse_allowed_roles,
    permanently_delete_document,
    replace_document_roles,
    to_document_response,
)


router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF document")],
    name: Annotated[str, Form(min_length=1, max_length=255)],
    allowed_roles: Annotated[
        str,
        Form(description='JSON array ["hr", "manager"] or comma list hr,manager'),
    ],
    classification: Annotated[Classification, Form()] = Classification.INTERNAL,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> DocumentUploadResponse:
    roles = parse_allowed_roles(allowed_roles)
    document = await create_document(
        session=session,
        settings=settings,
        upload=file,
        name=name,
        classification=classification,
        roles=roles,
        uploaded_by=principal.user_id,
    )
    # Ensure the row and storage metadata are committed before the isolated
    # background session attempts to lock and process it.
    await session.commit()
    background_tasks.add_task(run_ingestion_job, document.id)
    return DocumentUploadResponse(document_id=document.id, status=document.status)


@router.get("", response_model=DocumentListResponse)
async def get_documents(
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    del principal
    documents, total = await list_documents(session, limit, offset)
    return DocumentListResponse(
        items=[to_document_response(document) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/config", response_model=DocumentUploadConfigResponse)
async def get_document_upload_config(
    principal: Principal = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> DocumentUploadConfigResponse:
    """Return authoritative upload choices for the admin dashboard."""

    del principal
    return DocumentUploadConfigResponse(
        allowed_roles=list(AccessRole),
        classifications=list(Classification),
        max_upload_size_bytes=settings.max_upload_size_bytes,
        accepted_file_types=["application/pdf"],
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    del principal
    return to_document_response(await get_document_or_404(session, document_id))


@router.patch("/{document_id}/access", response_model=DocumentResponse)
async def update_document_access(
    document_id: uuid.UUID,
    update: RoleAccessUpdate,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    del principal
    document = await get_document_or_404(session, document_id)
    document = await replace_document_roles(session, document, update.allowed_roles)
    return to_document_response(document)


@router.get("/{document_id}/status", response_model=DocumentProcessingStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentProcessingStatusResponse:
    del principal
    document = await get_document_or_404(session, document_id)
    chunks_created, security_findings = await get_processing_counts(session, document_id)
    return DocumentProcessingStatusResponse(
        document_id=document.id,
        status=document.status,
        chunks_created=chunks_created,
        security_findings=security_findings,
    )


@router.post(
    "/{document_id}/process",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_document_processing(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    del principal
    document = await get_document_or_404(session, document_id)
    document.status = DocumentStatus.PROCESSING
    await session.commit()
    background_tasks.add_task(run_ingestion_job, document.id)
    return DocumentUploadResponse(document_id=document.id, status=document.status)


@router.post(
    "/{document_id}/activate",
    response_model=DocumentActivationResponse,
)
async def reactivate_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentActivationResponse:
    """Restore an inactive document to role-authorized retrieval."""

    del principal
    document = await get_document_or_404(session, document_id)
    document, requires_processing = await activate_document(session, document)
    await session.commit()
    if requires_processing:
        background_tasks.add_task(run_ingestion_job, document.id)
    return DocumentActivationResponse(
        document_id=document.id,
        status=document.status,
        reprocessing=requires_processing,
    )


@router.delete("/{document_id}", response_model=DocumentDeactivationResponse)
async def delete_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentDeactivationResponse:
    del principal
    document = await get_document_or_404(session, document_id)
    document = await deactivate_document(session, document)
    return DocumentDeactivationResponse(document_id=document.id, status=document.status)


@router.delete(
    "/{document_id}/permanent",
    response_model=DocumentPermanentDeletionResponse,
)
async def permanently_delete_document_route(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> DocumentPermanentDeletionResponse:
    """Permanently erase a document, its vector chunks, ACL, and stored PDF."""

    del principal
    document = await get_document_or_404(session, document_id)
    file_deleted = await permanently_delete_document(session, document, settings)
    return DocumentPermanentDeletionResponse(
        document_id=document_id,
        deleted=True,
        file_deleted=file_deleted,
    )
