from fastapi.testclient import TestClient

from app.database.init_db import seed_default_roles
from app.database.session import SessionLocal
from app.main import app
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.models.security_event import SecurityEvent
from app.models.token import RefreshToken
from app.models.user import User
from app.models.user_role import UserRole
from app.rag.models.audit import AuditEvent
from app.rag.models.document import Document
from app.utils.security import create_access_token, create_refresh_token, decode_token, hash_password


def test_tokens_are_unique_even_when_issued_in_the_same_second() -> None:
    """JWT IDs prevent duplicate refresh-token rows during rapid logins."""

    first_access = create_access_token("same-user", 1)
    second_access = create_access_token("same-user", 1)
    first_refresh = create_refresh_token("same-user")
    second_refresh = create_refresh_token("same-user")

    assert first_access != second_access
    assert first_refresh != second_refresh
    assert decode_token(first_access)["jti"] != decode_token(second_access)["jti"]
    assert decode_token(first_refresh)["jti"] != decode_token(second_refresh)["jti"]


def _clear_data() -> None:
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
    seed_default_roles()


def test_registration_uses_default_user_role_and_auth_flow() -> None:
    _clear_data()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Alice Example",
                "email": "alice@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "active"
        assert payload["access_token"]
        assert payload["refresh_token"]

        db = SessionLocal()
        try:
            role = db.query(Role).filter(Role.name == "Employee").first()
            user = db.query(User).filter(User.email == "alice@example.com").first()
        finally:
            db.close()

        assert role is not None
        assert user is not None
        assert user.role_id == role.id

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "alice@example.com"

        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": payload["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        refreshed = refresh_response.json()
        assert refreshed["access_token"]

        logout_response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": payload["refresh_token"]},
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        assert logout_response.status_code == 200

        revoked_access_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        assert revoked_access_response.status_code == 401


def test_privileged_registration_requires_administrator_approval() -> None:
    _clear_data()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Manager Applicant",
                "email": "manager-applicant@example.com",
                "password": "password123",
                "confirm_password": "password123",
                "requested_role": "Manager",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "pending_approval"
        assert payload["access_token"] is None
        assert payload["refresh_token"] is None

        blocked_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "manager-applicant@example.com",
                "password": "password123",
                "login_as": "Manager",
                "portal": "employee",
            },
        )
        assert blocked_login.status_code == 401

        admin_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@sentinelai.com",
                "password": "sentinelai123",
                "portal": "administrator",
            },
        )
        assert admin_login.status_code == 200
        admin_headers = {
            "Authorization": f"Bearer {admin_login.json()['access_token']}"
        }
        users = client.get("/api/v1/users", headers=admin_headers)
        applicant = next(
            item
            for item in users.json()
            if item["email"] == "manager-applicant@example.com"
        )
        approval = client.patch(
            f"/api/v1/users/{applicant['id']}/status",
            headers=admin_headers,
            json={"is_active": True},
        )
        assert approval.status_code == 200
        assert approval.json()["is_active"] is True
        assert approval.json()["is_verified"] is True

        approved_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "manager-applicant@example.com",
                "password": "password123",
                "login_as": "Manager",
                "portal": "employee",
            },
        )
        assert approved_login.status_code == 200
        profile = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {approved_login.json()['access_token']}"
            },
        )
        assert profile.status_code == 200
        assert profile.json()["role_name"] == "Manager"


def test_rbac_blocks_non_admin_access_to_protected_routes() -> None:
    _clear_data()
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "SentinelAI Administrator").first()
        user_role = db.query(Role).filter(Role.name == "Employee").first()
        if not admin_role or not user_role:
            raise AssertionError("Expected seeded roles")

        admin_user = User(
            name="Admin User",
            email="platform-admin@example.com",
            password_hash=hash_password("password123"),
            role_id=admin_role.id,
            is_verified=True,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        regular_user = User(
            name="Regular User",
            email="regular@example.com",
            password_hash=hash_password("password123"),
            role_id=user_role.id,
            is_verified=True,
            is_active=True,
        )
        db.add(regular_user)
        db.commit()
        db.refresh(regular_user)
    finally:
        db.close()

    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "platform-admin@example.com", "password": "password123", "portal": "administrator"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        admin_roles_response = client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_roles_response.status_code == 200

        user_login = client.post(
            "/api/v1/auth/login",
            json={"email": "regular@example.com", "password": "password123", "login_as": "Employee", "portal": "employee"},
        )
        assert user_login.status_code == 200
        user_token = user_login.json()["access_token"]

        user_roles_response = client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert user_roles_response.status_code == 403
