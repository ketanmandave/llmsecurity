"""Documents and their role-based access-control entries."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AccessRole, Classification, DocumentStatus, enum_values

if TYPE_CHECKING:
    from app.models.chunk import Chunk


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    classification: Mapped[Classification] = mapped_column(
        Enum(
            Classification,
            name="classification",
            values_callable=enum_values,
            validate_strings=True,
        ),
        default=Classification.INTERNAL,
        server_default=Classification.INTERNAL.value,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        default=DocumentStatus.PROCESSING,
        server_default=DocumentStatus.PROCESSING.value,
        index=True,
    )
    uploaded_by: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list["DocumentRole"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentRole(Base):
    __tablename__ = "document_roles"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[AccessRole] = mapped_column(
        Enum(
            AccessRole,
            name="access_role",
            values_callable=enum_values,
            validate_strings=True,
        ),
        primary_key=True,
    )

    document: Mapped[Document] = relationship(back_populates="roles")
