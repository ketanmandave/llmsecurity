"""Service health-check routes."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.database import engine


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: the web process is running."""

    return {"status": "healthy"}


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


async def _redis_ready(settings: Settings) -> bool:
    if not settings.rate_limit_enabled:
        return True
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        return bool(await client.ping())
    except RedisError:
        return False
    finally:
        await client.aclose()


@router.get("/ready")
async def readiness(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    """Readiness check for traffic-critical database and Redis dependencies."""

    database_ok, redis_ok = await asyncio.gather(
        _database_ready(),
        _redis_ready(settings),
    )
    ready = database_ok and redis_ok
    return JSONResponse(
        status_code=(
            status.HTTP_200_OK
            if ready
            else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content={
            "status": "ready" if ready else "not_ready",
            "database": "healthy" if database_ok else "unavailable",
            "redis": (
                "disabled"
                if not settings.rate_limit_enabled
                else "healthy" if redis_ok else "unavailable"
            ),
        },
    )
