from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.services.redis_service import RedisService


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int | None = None, window_seconds: int | None = None) -> None:
        super().__init__(app)
        self.max_requests = max_requests or settings.redis_rate_limit_max_requests
        self.window_seconds = window_seconds or settings.redis_rate_limit_window_seconds
        self.redis_service = RedisService()

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in {"/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = int(time())
        window_key = f"ratelimit:{request.url.path}:{client_ip}"
        current = self.redis_service.get_value(window_key) or []
        if not isinstance(current, list):
            current = []
        current = [stamp for stamp in current if stamp > now - self.window_seconds]
        if len(current) >= self.max_requests:
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        current.append(now)
        self.redis_service.set_value(window_key, current, ttl_seconds=self.window_seconds)
        return await call_next(request)
