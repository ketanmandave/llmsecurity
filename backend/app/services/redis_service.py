import json
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - defensive fallback
    redis = None

from app.core.config import settings


class RedisService:
    _fallback_store: dict[str, Any] = {}

    def __init__(self, client: Any | None = None) -> None:
        self.client = client
        self._use_fallback = False

        if client is None:
            if redis is None:
                self._use_fallback = True
                self.client = None
            else:
                try:
                    self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                    self.client.ping()
                except Exception:
                    self._use_fallback = True
                    self.client = None
        else:
            try:
                if hasattr(client, "ping"):
                    client.ping()
            except Exception:
                self._use_fallback = True
                self.client = None

    def _serialize(self, value: Any) -> str | Any:
        return json.dumps(value) if not isinstance(value, str) else value

    def _deserialize(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def _get_fallback_value(self, key: str) -> Any | None:
        return self._fallback_store.get(key)

    def _set_fallback_value(self, key: str, value: Any) -> None:
        self._fallback_store[key] = value

    def _delete_fallback_value(self, key: str) -> None:
        self._fallback_store.pop(key, None)

    def set_value(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        payload = self._serialize(value)
        if self._use_fallback or self.client is None:
            self._set_fallback_value(key, payload)
            return

        try:
            self.client.set(key, payload, ex=ttl_seconds)
        except Exception:
            self._use_fallback = True
            self._set_fallback_value(key, payload)

    def get_value(self, key: str) -> Any | None:
        if self._use_fallback or self.client is None:
            return self._deserialize(self._get_fallback_value(key))

        try:
            value = self.client.get(key)
            return self._deserialize(value)
        except Exception:
            self._use_fallback = True
            return self._deserialize(self._get_fallback_value(key))

    def delete_value(self, key: str) -> None:
        if self._use_fallback or self.client is None:
            self._delete_fallback_value(key)
            return

        try:
            self.client.delete(key)
        except Exception:
            self._use_fallback = True
            self._delete_fallback_value(key)

    def add_to_set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if self._use_fallback or self.client is None:
            current = self._fallback_store.get(key)
            if current is None:
                self._fallback_store[key] = {value}
            elif isinstance(current, set):
                current.add(value)
            else:
                self._fallback_store[key] = {current, value}
            return

        try:
            self.client.sadd(key, value)
            if ttl_seconds:
                self.client.expire(key, ttl_seconds)
        except Exception:
            self._use_fallback = True
            current = self._fallback_store.get(key)
            if current is None:
                self._fallback_store[key] = {value}
            elif isinstance(current, set):
                current.add(value)
            else:
                self._fallback_store[key] = {current, value}

    def set_member(self, key: str, value: str) -> bool:
        if self._use_fallback or self.client is None:
            current = self._fallback_store.get(key)
            return isinstance(current, set) and value in current

        try:
            return bool(self.client.sismember(key, value))
        except Exception:
            self._use_fallback = True
            current = self._fallback_store.get(key)
            return isinstance(current, set) and value in current

    def delete_from_set(self, key: str, value: str) -> None:
        if self._use_fallback or self.client is None:
            current = self._fallback_store.get(key)
            if isinstance(current, set):
                current.discard(value)
            return

        try:
            self.client.srem(key, value)
        except Exception:
            self._use_fallback = True
            current = self._fallback_store.get(key)
            if isinstance(current, set):
                current.discard(value)
