"""Integration-contract tests for SentinelAI identity and Secure RAG ACLs."""

from app.models.role import Role
from app.models.user import User
from app.rag.auth.jwt import normalize_role_slug, principal_from_user
from app.rag.models import AuditEvent, Document, DocumentRole


def test_principal_uses_sentinel_user_and_database_role() -> None:
    role = Role(id=42, name="Security Analyst")
    user = User(
        id="user-42",
        name="Security User",
        email="security-user@example.com",
        password_hash="not-used-by-this-test",
        role_id=role.id,
        is_verified=True,
        is_active=True,
    )
    user.role = role

    principal = principal_from_user(user)

    assert principal.user_id == user.id
    assert principal.role_id == role.id
    assert principal.role_ids == frozenset({role.id})
    assert principal.role_slug == "security_analyst"
    assert normalize_role_slug("Payroll Administrator") == "payroll_administrator"


def test_rag_acl_columns_reference_sentinel_tables() -> None:
    document_uploader_fk = next(iter(Document.__table__.c.uploaded_by.foreign_keys))
    document_role_fk = next(iter(DocumentRole.__table__.c.role_id.foreign_keys))
    audit_user_fk = next(iter(AuditEvent.__table__.c.user_id.foreign_keys))

    assert document_uploader_fk.target_fullname == "users.id"
    assert document_role_fk.target_fullname == "roles.id"
    assert audit_user_fk.target_fullname == "users.id"

