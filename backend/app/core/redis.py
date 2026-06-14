"""Redis client (cache, rate limiting, refresh-token denylist, agent memory)."""
from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    # Fail fast instead of hanging when Redis is unreachable (middleware fails open).
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
    retry_on_timeout=False,
)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency returning the shared Redis client."""
    return redis_client
