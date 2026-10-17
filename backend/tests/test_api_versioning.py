from fastapi.testclient import TestClient

from app.main import app


def test_root_route_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200


def test_auth_routes_are_versioned() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "doesnotexist@example.com", "password": "wrong", "portal": "employee"},
        )
    assert response.status_code == 401


def test_login_preflight_allows_local_frontend_origins() -> None:
    """Both common local hostnames must receive valid credentialed CORS headers."""

    with TestClient(app) as client:
        for origin in ("http://localhost:5174", "http://127.0.0.1:5174"):
            response = client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert response.headers["access-control-allow-credentials"] == "true"
