"""Document chunks and their vector embeddings."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.rag.config import EMBEDDING_DIMENSION
from app.rag.models.base import Base
from app.rag.models.enums import SecurityStatus, enum_values

if TYPE_CHECKING:
    from app.rag.models.document import Document


class Chunk(Base):
    """Role-gated document passage and its pgvector embedding."""

    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="chunk_index_nonnegative"),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="page_positive"),
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_document_index"),
        Index("ix_chunks_document_security", "document_id", "security_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    content_type: Mapped[str] = mapped_column(
        String(40), default="text", server_default="text", index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(40), default="pymupdf", server_default="pymupdf", index=True
    )
    token_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    extraction_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    security_status: Mapped[SecurityStatus] = mapped_column(
        Enum(
            SecurityStatus,
            name="security_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        default=SecurityStatus.PENDING,
        server_default=SecurityStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")
