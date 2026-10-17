"""Atomic Redis-backed per-user rate limiting."""

import hashlib
from functools import lru_cache

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.rag.config import Settings, get_settings


RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""


class RateLimitExceeded(RuntimeError):
    """Raised with a retry delay when a user exceeds the configured window."""

    def __init__(self, retry_after: int) -> None:
        """Normalize Redis TTL into a positive Retry-After value."""

        self.retry_after = max(retry_after, 1)
        super().__init__("Rate limit exceeded")


class RateLimitUnavailable(RuntimeError):
    """Raised when rate limiting cannot be enforced."""


class RateLimiter:
    """Enforce an atomic fixed-window request limit keyed by hashed user ID."""

    def __init__(self, settings: Settings) -> None:
        """Build the Redis client and copy rate-limit policy from settings."""

        self.enabled = settings.rate_limit_enabled
        self.limit = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def check(self, user_id: str) -> None:
        """Consume one request slot or fail closed if Redis is unavailable."""

        if not self.enabled:
            return
        user_key = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        key = f"secure-rag:rate:{user_key}"
        try:
            count, ttl = await self.redis.eval(
                RATE_LIMIT_SCRIPT,
                1,
                key,
                self.window_seconds,
            )
        except RedisError as exc:
            raise RateLimitUnavailable("Rate-limit store is unavailable") from exc
        if int(count) > self.limit:
            raise RateLimitExceeded(int(ttl))


@lru_cache
def get_rate_limiter() -> RateLimiter:
    """Return the process-wide rate limiter used by query endpoints."""

    return RateLimiter(get_settings())
