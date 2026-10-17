from fastapi.testclient import TestClient

from app.database.init_db import init_db
from app.database.session import SessionLocal
from app.main import app
from app.core.config import settings
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.models.security_event import SecurityEvent
from app.models.token import RefreshToken
from app.models.user import User
from app.models.user_role import UserRole
from app.rag.models.audit import AuditEvent
from app.rag.models.document import Document
from app.services.auth_service import AuthService
from app.services.redis_service import RedisService
from app.services.session_service import SessionService
from app.utils.security import hash_password


def _setup_test_state() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Test-only reset: remove dependent security/RAG records before users.
        db.query(AuditEvent).delete()
        db.query(Document).delete()
        db.query(SecurityEvent).delete()
        db.query(Message).delete()
        db.query(Conversation).delete()
        db.query(RefreshToken).delete()
        db.query(AuditLog).delete()
        db.query(UserRole).delete()
        db.query(User).delete()
        db.query(Role).delete()
        db.commit()
    finally:
        db.close()
    init_db()


def test_token_revocation_and_session_storage() -> None:
    _setup_test_state()
    db = SessionLocal()
    try:
        user = User(
            name="Redis User",
            email="redis@example.com",
            password_hash=hash_password("password123"),
            role_id=db.query(Role).filter(Role.name == "Employee").first().id,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    finally:
        db.close()

    auth_service = AuthService(SessionLocal())
    user, access_token, refresh_token = auth_service.login("redis@example.com", "password123", "Employee", "employee")
    assert user.id
    session_service = SessionService(RedisService())
    assert session_service.get_session(user.id) == refresh_token
    auth_service.revoke_token(refresh_token)
    assert RedisService().get_value(f"blacklist:{refresh_token}") is True
    auth_service.logout(refresh_token)


def test_rate_limiting_on_auth_endpoints() -> None:
    _setup_test_state()
    key = "ratelimit:/api/v1/auth/login:testclient"
    RedisService().delete_value(key)
    with TestClient(app) as client:
        for _ in range(settings.redis_rate_limit_max_requests):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "missing@example.com", "password": "wrong", "portal": "employee"},
            )
            assert response.status_code in {401, 429}
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong", "portal": "employee"},
        )
        assert response.status_code == 429
    RedisService().delete_value(key)
