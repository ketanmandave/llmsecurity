from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.demo_users import DEMO_ROLES, DEMO_USERS
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import audit_log, conversation, permission, role, role_permission, security_event, setting, token, user, user_role
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models.token import RefreshToken
from app.models.user import User
from app.models.user_role import UserRole
from app.rag import models as rag_models  # noqa: F401 - registers RAG tables
from app.utils.security import hash_password


def init_db() -> None:
    ensure_pgvector_extension()
    Base.metadata.create_all(bind=engine)
    ensure_rag_search_indexes()
    ensure_conversation_columns()
    ensure_message_rag_columns()
    ensure_security_event_columns()
    ensure_security_event_conversation_reference()
    seed_default_roles()


def ensure_pgvector_extension() -> None:
    """Enable the PostgreSQL vector type required by RAG chunk embeddings."""

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def ensure_rag_search_indexes() -> None:
    """Create additive lexical indexes used by hybrid RAG retrieval."""

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_content_fts "
                "ON chunks USING gin (to_tsvector('english', content))"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_documents_name_fts "
                "ON documents USING gin (to_tsvector('simple', name))"
            )
        )


def ensure_conversation_columns() -> None:
    """Apply additive conversation columns for databases initialized earlier."""
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE conversations ADD COLUMN IF NOT EXISTS "title" VARCHAR(120)'))
        connection.execute(text("UPDATE conversations SET title = 'New conversation' WHERE title IS NULL"))
        connection.execute(text('ALTER TABLE conversations ALTER COLUMN "title" SET DEFAULT \'New conversation\''))
        connection.execute(text('ALTER TABLE conversations ALTER COLUMN "title" SET NOT NULL'))


def ensure_message_rag_columns() -> None:
    """Add conversation-mode and citation fields without replacing existing data."""

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS mode "
                "VARCHAR(20) NOT NULL DEFAULT 'assistant'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS citations "
                "JSON NOT NULL DEFAULT '[]'::json"
            )
        )
        connection.execute(
            text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS request_id VARCHAR(36)")
        )
        connection.execute(
            text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS grounded BOOLEAN")
        )
        connection.execute(
            text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS model VARCHAR(120)")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_messages_request_id "
                "ON messages (request_id)"
            )
        )


def ensure_security_event_columns() -> None:
    """Apply only additive Phase 3.7 columns for databases initialized earlier."""
    columns = {
        "prompt": "TEXT",
        "authorization_decision": "VARCHAR(20)",
        "authorization_reason": "VARCHAR(500)",
        "detector_results": "JSON",
        "outcome": "VARCHAR(30)",
        "provider_status_code": "INTEGER",
        "response_assessment": "JSON",
        "response_outcome": "VARCHAR(30)",
        "latency_ms": "DOUBLE PRECISION",
        "metadata_json": "JSON",
        "error_type": "VARCHAR(200)",
        "error_message": "VARCHAR(1000)",
    }
    with engine.begin() as connection:
        for name, sql_type in columns.items():
            connection.execute(text(f'ALTER TABLE security_events ADD COLUMN IF NOT EXISTS "{name}" {sql_type}'))
        for index_name, columns_sql in {
            "ix_security_events_conversation_timestamp": '"conversation_id", "event_timestamp"',
            "ix_security_events_user_timestamp": '"user_id", "event_timestamp"',
            "ix_security_events_authorization_decision": '"authorization_decision"',
        }.items():
            connection.execute(text(f'CREATE INDEX IF NOT EXISTS "{index_name}" ON security_events ({columns_sql})'))


def ensure_security_event_conversation_reference() -> None:
    """Keep audit events when their user-owned conversation is deleted."""
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE security_events ALTER COLUMN conversation_id DROP NOT NULL"))
        connection.execute(text("""
            DO $$
            DECLARE constraint_name text;
            BEGIN
                FOR constraint_name IN
                    SELECT pg_constraint.conname
                    FROM pg_constraint
                    JOIN pg_class ON pg_class.oid = pg_constraint.conrelid
                    JOIN pg_attribute ON pg_attribute.attrelid = pg_constraint.conrelid
                        AND pg_attribute.attnum = ANY(pg_constraint.conkey)
                    WHERE pg_class.relname = 'security_events'
                      AND pg_constraint.contype = 'f'
                      AND pg_attribute.attname = 'conversation_id'
                LOOP
                    EXECUTE format('ALTER TABLE security_events DROP CONSTRAINT %I', constraint_name);
                END LOOP;
            END $$;
        """))
        connection.execute(text("""
            ALTER TABLE security_events
            ADD CONSTRAINT security_events_conversation_id_fkey
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
        """))


def seed_default_roles() -> None:
    db: Session = SessionLocal()
    try:
        existing_roles = {item.name for item in db.query(Role).all()}
        defaults = list(DEMO_ROLES)
        for name, description in defaults:
            if name not in existing_roles:
                db.add(Role(name=name, description=description))

        db.flush()
        legacy_admin = db.query(User).filter(User.email == "admin@example.com").first()
        if legacy_admin:
            db.query(RefreshToken).filter(RefreshToken.user_id == legacy_admin.id).delete()
            db.query(AuditLog).filter(AuditLog.user_id == legacy_admin.id).delete()
            db.query(UserRole).filter(UserRole.user_id == legacy_admin.id).delete()
            db.delete(legacy_admin)
            db.flush()

        role_by_name = {role.name: role for role in db.query(Role).all()}
        for name, email, password in DEMO_USERS:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(name=name, email=email, password_hash=hash_password(password), role_id=role_by_name[name].id, is_verified=True, is_active=True))
        db.commit()
    finally:
        db.close()
