"""Public-route and authentication-boundary tests for integrated Secure RAG."""

from collections.abc import Callable, Iterator

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.main import app
from app.rag.auth.jwt import get_current_principal
from app.rag.auth.permissions import require_admin


def _rag_routes() -> list[APIRoute]:
    """Return only application routes exposed through the RAG namespace."""

    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/rag")
    ]


def _dependency_calls(dependant: Dependant) -> Iterator[Callable[..., object]]:
    """Walk a route's complete FastAPI dependency tree."""

    for child in dependant.dependencies:
        if child.call is not None:
            yield child.call
        yield from _dependency_calls(child)


def test_integrated_rag_routes_match_the_public_contract() -> None:
    routes = _rag_routes()
    exposed = {
        (route.path, method)
        for route in routes
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }

    expected = {
        ("/api/v1/rag/query", "POST"),
        ("/api/v1/rag/retrieval/search", "POST"),
        ("/api/v1/rag/documents", "POST"),
        ("/api/v1/rag/documents", "GET"),
        ("/api/v1/rag/documents/config", "GET"),
        ("/api/v1/rag/documents/{document_id}", "GET"),
        ("/api/v1/rag/documents/{document_id}/access", "PATCH"),
        ("/api/v1/rag/documents/{document_id}/status", "GET"),
        ("/api/v1/rag/documents/{document_id}/process", "POST"),
        ("/api/v1/rag/documents/{document_id}/activate", "POST"),
        ("/api/v1/rag/documents/{document_id}", "DELETE"),
        ("/api/v1/rag/documents/{document_id}/permanent", "DELETE"),
    }

    assert exposed == expected
    assert not any(route.path.startswith("/v1/") for route in app.routes)


def test_rag_routes_reuse_sentinel_authentication_dependencies() -> None:
    routes = _rag_routes()
    admin_routes = [route for route in routes if "/documents" in route.path]
    user_routes = [route for route in routes if route not in admin_routes]

    assert admin_routes
    assert user_routes
    assert all(require_admin in set(_dependency_calls(route.dependant)) for route in admin_routes)
    assert all(
        get_current_principal in set(_dependency_calls(route.dependant))
        for route in user_routes
    )


def test_openapi_publishes_rag_routes_under_one_namespace() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/rag/query" in paths
    assert "/api/v1/rag/retrieval/search" in paths
    assert "/api/v1/rag/documents" in paths
