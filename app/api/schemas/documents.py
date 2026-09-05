"""Document-management API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AccessRole, Classification, DocumentStatus


class DocumentUploadConfigResponse(BaseModel):
    allowed_roles: list[AccessRole]
    classifications: list[Classification]
    max_upload_size_bytes: int
    accepted_file_types: list[str]


class RoleAccessUpdate(BaseModel):
    """Complete replacement for a document's allowed roles."""

    allowed_roles: list[AccessRole] = Field(min_length=1, max_length=4)

    @field_validator("allowed_roles")
    @classmethod
    def roles_must_be_unique(cls, roles: list[AccessRole]) -> list[AccessRole]:
        if len(roles) != len(set(roles)):
            raise ValueError("allowed_roles must not contain duplicates")
        return roles


class DocumentResponse(BaseModel):
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
    allowed_roles: list[AccessRole]
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus


class DocumentDeactivationResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus


class DocumentActivationResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus
    reprocessing: bool


class DocumentPermanentDeletionResponse(BaseModel):
    document_id: uuid.UUID
    deleted: bool
    file_deleted: bool


class DocumentProcessingStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus
    chunks_created: int
    security_findings: int
