"""Cache port + implementations for hot read paths (e.g. analytics).

A tiny async cache abstraction: ``InMemoryCache`` (TTL, process-local) for dev/tests,
``RedisCache`` for multi-replica production. Values are JSON-serializable dicts.
"""
from __future__ import annotations

import json
import time
from typing import Any, Protocol, runtime_checkable

from app.core.config import settings


@runtime_checkable
class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int) -> None: ...
    async def delete(self, key: str) -> None: ...


class InMemoryCache:
    """Process-local TTL cache. Correct for a single replica / tests."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.monotonic() + ttl, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


class RedisCache:
    """Shared cache across replicas. Fails open (treated as a miss) if Redis is down."""

    def __init__(self, client) -> None:  # noqa: ANN001
        self._redis = client

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl)
        except Exception:
            pass

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:
            pass


# Process-local singleton (used directly in tests / single-replica dev).
_in_memory = InMemoryCache()


def get_cache() -> Cache:
    if settings.ENVIRONMENT == "test" or not settings.CACHE_ENABLED:
        return _in_memory
    from app.core.redis import redis_client

    return RedisCache(redis_client)
