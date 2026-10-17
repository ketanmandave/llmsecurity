from fastapi.testclient import TestClient

from app.core.demo_users import DEMO_USERS
from app.database.init_db import seed_default_roles
from app.main import app
from app.services.redis_service import RedisService
from app.utils.security import decode_token


def test_demo_users_portals_and_conversation_ownership() -> None:
    seed_default_roles()
    RedisService().delete_value("ratelimit:/api/v1/auth/login:testclient")
    conversations: dict[str, tuple[dict[str, str], str]] = {}
    with TestClient(app) as client:
        for role, email, password in DEMO_USERS:
            payload = {"email": email, "password": password, "portal": "administrator" if role == "SentinelAI Administrator" else "employee"}
            if role != "SentinelAI Administrator":
                payload["login_as"] = role
            login = client.post("/api/v1/auth/login", json=payload)
            assert login.status_code == 200
            token = login.json()["access_token"]
            assert decode_token(token)["role_id"]
            headers = {"Authorization": f"Bearer {token}"}
            me = client.get("/api/v1/auth/me", headers=headers)
            assert me.status_code == 200 and me.json()["role_name"] == role
            workspace = client.get("/api/v1/workspace/conversations", headers=headers)
            assert workspace.status_code == (403 if role == "SentinelAI Administrator" else 200)
            console = client.get("/api/v1/roles", headers=headers)
            assert console.status_code == (200 if role == "SentinelAI Administrator" else 403)
            if workspace.status_code == 200:
                created = client.post("/api/v1/workspace/conversations", headers=headers)
                assert created.status_code == 201
                conversations[role] = (headers, created.json()["id"])

        for role, (headers, conversation_id) in conversations.items():
            listed = client.get("/api/v1/workspace/conversations", headers=headers)
            ids = {item["id"] for item in listed.json()}
            assert conversation_id in ids
            for other_role, (_, other_id) in conversations.items():
                if other_role != role:
                    assert client.get(f"/api/v1/workspace/conversations/{other_id}", headers=headers).status_code == 404


def test_cross_portal_and_legacy_admin_are_rejected() -> None:
    RedisService().delete_value("ratelimit:/api/v1/auth/login:testclient")
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login", json={"email": "employee@company.com", "password": "employee123", "portal": "administrator"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"email": "admin@sentinelai.com", "password": "sentinelai123", "login_as": "Employee", "portal": "employee"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "Admin123!", "portal": "administrator"}).status_code == 401
