from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.database.session import engine

try:
    import redis
except ImportError:  # pragma: no cover - defensive fallback
    redis = None

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    database_status = "ok"
    redis_status = "ok"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "error"

    if redis is not None:
        try:
            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
        except Exception:
            redis_status = "error"
    else:
        redis_status = "error"

    return {
        "backend_status": "ok",
        "database_status": database_status,
        "redis_status": redis_status,
    }
