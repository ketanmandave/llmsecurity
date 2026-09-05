"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.query import router as retrieval_router
from app.api.rag import router as rag_router
from app.config import get_settings


settings = get_settings()
admin_ui_directory = Path(__file__).parent / "static" / "admin"
app = FastAPI(title=settings.app_name)
if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(rag_router)
app.mount(
    "/admin/assets",
    StaticFiles(directory=admin_ui_directory),
    name="admin-assets",
)


@app.get("/admin", include_in_schema=False)
async def admin_dashboard() -> FileResponse:
    """Serve the integrated administrator document dashboard."""

    return FileResponse(
        admin_ui_directory / "index.html",
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )
