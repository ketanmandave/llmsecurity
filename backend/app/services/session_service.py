from app.services.redis_service import RedisService


class SessionService:
    def __init__(self, redis_service: RedisService | None = None) -> None:
        self.redis_service = redis_service or RedisService()

    def store_session(self, user_id: str, session_id: str) -> None:
        self.redis_service.set_value(f"session:{user_id}", session_id, ttl_seconds=3600)

    def get_session(self, user_id: str) -> str | None:
        return self.redis_service.get_value(f"session:{user_id}")

    def delete_session(self, user_id: str) -> None:
        self.redis_service.delete_value(f"session:{user_id}")
