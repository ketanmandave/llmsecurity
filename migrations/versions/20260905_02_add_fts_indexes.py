"""Add full-text indexes for hybrid retrieval.

Revision ID: 20260905_02
Revises: 20260904_01
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260905_02"
down_revision: str | None = "20260904_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_chunks_content_fts ON chunks "
        "USING gin (to_tsvector('english', content))"
    )
    op.execute(
        "CREATE INDEX ix_documents_name_fts ON documents "
        "USING gin (to_tsvector('simple', name))"
    )


def downgrade() -> None:
    op.drop_index("ix_documents_name_fts", table_name="documents")
    op.drop_index("ix_chunks_content_fts", table_name="chunks")
