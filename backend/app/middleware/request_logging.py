import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("sentinelai")
logger.setLevel(logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            status_code = 500
            raise exc
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
                "user_id": getattr(request.state, "user_id", None),
                "email": getattr(request.state, "user_email", None),
                "ip": request.client.host if request.client else None,
                "endpoint": request.url.path,
                "method": request.method,
                "status": status_code,
                "latency_ms": duration_ms,
                "role": getattr(request.state, "user_role_id", None),
            }
            logger.info(json.dumps(payload))
