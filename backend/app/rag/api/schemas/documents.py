"""Document-management API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.rag.models.enums import Classification, DocumentStatus


class RoleOption(BaseModel):
    """SentinelAI role exposed for administrator ACL selection."""

    id: int
    name: str
    slug: str


class DocumentUploadConfigResponse(BaseModel):
    """Server-controlled choices and limits consumed by the admin upload form."""

    allowed_roles: list[RoleOption]
    classifications: list[Classification]
    max_upload_size_bytes: int
    accepted_file_types: list[str]
    native_text_only: bool


class RoleAccessUpdate(BaseModel):
    """Complete replacement for a document's allowed roles."""

    allowed_role_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("allowed_role_ids")
    @classmethod
    def roles_must_be_unique(cls, roles: list[int]) -> list[int]:
        """Reject duplicate role entries before replacing a document ACL."""

        if len(roles) != len(set(roles)):
            raise ValueError("allowed_role_ids must not contain duplicates")
        if any(role_id < 1 for role_id in roles):
            raise ValueError("allowed_role_ids must contain positive IDs")
        return roles


class DocumentResponse(BaseModel):
    """Complete administrator-facing document metadata and role assignment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    original_filename: str
    mime_type: str
    checksum_sha256: str
    size_bytes: int
    classification: Classification
    status: DocumentStatus
    uploaded_by: str
    total_pages: int | None
    processing_error: str | None
    metadata: dict
    allowed_roles: list[RoleOption]
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated collection of administrator-facing document records."""

    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentUploadResponse(BaseModel):
    """Acknowledgement returned when document processing has been queued."""

    document_id: uuid.UUID
    status: DocumentStatus


class DocumentDeactivationResponse(BaseModel):
    """Result returned after a document is removed from retrieval."""

    document_id: uuid.UUID
    status: DocumentStatus


class DocumentActivationResponse(BaseModel):
    """Activation result indicating whether vectors must be rebuilt."""

    document_id: uuid.UUID
    status: DocumentStatus
    reprocessing: bool


class DocumentPermanentDeletionResponse(BaseModel):
    """Permanent-delete result for database data and the stored PDF."""

    document_id: uuid.UUID
    deleted: bool
    file_deleted: bool


class DocumentProcessingStatusResponse(BaseModel):
    """Current ingestion state and counts used for dashboard polling."""

    document_id: uuid.UUID
    status: DocumentStatus
    chunks_created: int
    security_findings: int
