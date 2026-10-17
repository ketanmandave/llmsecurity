from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.routes import auth, audit_logs, dashboard, health, roles, security_events, settings as settings_routes, users, workspace
from app.core.config import settings
from app.database.init_db import init_db
from app.middleware.exception_handler import ExceptionHandlerMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.rag.api.router import router as rag_router

app = FastAPI(title="SentinelAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(audit_logs.router, prefix="/api/v1/audit-logs", tags=["audit-logs"])
app.include_router(security_events.router, prefix="/api/v1/security-events", tags=["security-events"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(workspace.router, prefix="/api/v1/workspace", tags=["workspace"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(rag_router, prefix="/api/v1/rag")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return await ExceptionHandlerMiddleware.handle_validation_error(request, exc)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return await ExceptionHandlerMiddleware.handle_http_exception(request, exc)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    return await ExceptionHandlerMiddleware.handle_generic_error(request, exc)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse({"message": "SentinelAI API is online"})
