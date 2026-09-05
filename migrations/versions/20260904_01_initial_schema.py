"""Create the secure RAG database schema.

Revision ID: 20260904_01
Revises: None
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision: str = "20260904_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


access_role = postgresql.ENUM(
    "admin", "hr", "manager", "employee", name="access_role", create_type=False
)
classification = postgresql.ENUM(
    "public", "internal", "confidential", "restricted",
    name="classification",
    create_type=False,
)
document_status = postgresql.ENUM(
    "processing", "active", "quarantined", "failed", "inactive",
    name="document_status",
    create_type=False,
)
security_status = postgresql.ENUM(
    "pending", "approved", "quarantined", "rejected",
    name="security_status",
    create_type=False,
)
policy_decision = postgresql.ENUM(
    "allow", "modify", "block", "quarantine",
    name="policy_decision",
    create_type=False,
)
severity = postgresql.ENUM(
    "info", "low", "medium", "high", "critical",
    name="severity",
    create_type=False,
)
finding_status = postgresql.ENUM(
    "open", "resolved", "accepted", name="finding_status", create_type=False
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    bind = op.get_bind()
    for enum_type in (
        access_role,
        classification,
        document_status,
        security_status,
        policy_decision,
        severity,
        finding_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("classification", classification, server_default="internal", nullable=False),
        sa.Column("status", document_status, server_default="processing", nullable=False),
        sa.Column("uploaded_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index("ix_documents_checksum_sha256", "documents", ["checksum_sha256"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])

    op.create_table(
        "document_roles",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("role", access_role, nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            name="fk_document_roles_document_id_documents", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("document_id", "role", name="pk_document_roles"),
    )
    op.create_index("ix_document_roles_role", "document_roles", ["role"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("security_status", security_status, server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("chunk_index >= 0", name="ck_chunks_chunk_index_nonnegative"),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0", name="ck_chunks_page_positive"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            name="fk_chunks_document_id_documents", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_chunk_document_index"
        ),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index(
        "ix_chunks_document_security", "chunks", ["document_id", "security_status"]
    )
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("user_roles", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("decision", policy_decision, nullable=False),
        sa.Column("document_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_decision", "audit_events", ["decision"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])

    op.create_table(
        "security_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", finding_status, server_default="open", nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_security_findings_confidence_range",
        ),
        sa.CheckConstraint(
            "document_id IS NOT NULL OR chunk_id IS NOT NULL",
            name="ck_security_findings_finding_has_source",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["chunks.id"],
            name="fk_security_findings_chunk_id_chunks", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            name="fk_security_findings_document_id_documents", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_security_findings"),
    )
    op.create_index("ix_security_findings_category", "security_findings", ["category"])
    op.create_index("ix_security_findings_chunk_id", "security_findings", ["chunk_id"])
    op.create_index("ix_security_findings_document_id", "security_findings", ["document_id"])
    op.create_index("ix_security_findings_severity", "security_findings", ["severity"])
    op.create_index("ix_security_findings_status", "security_findings", ["status"])


def downgrade() -> None:
    op.drop_table("security_findings")
    op.drop_table("audit_events")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("document_roles")
    op.drop_table("documents")

    bind = op.get_bind()
    for enum_type in (
        finding_status,
        severity,
        policy_decision,
        security_status,
        document_status,
        classification,
        access_role,
    ):
        enum_type.drop(bind, checkfirst=True)
