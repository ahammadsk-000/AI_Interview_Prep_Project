"""Unit tests for the in-memory cache."""
from __future__ import annotations

import asyncio

import pytest

from app.core.cache import InMemoryCache


@pytest.mark.asyncio
async def test_set_get_delete():
    cache = InMemoryCache()
    assert await cache.get("k") is None
    await cache.set("k", {"a": 1}, ttl=30)
    assert await cache.get("k") == {"a": 1}
    await cache.delete("k")
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_ttl_expiry():
    cache = InMemoryCache()
    await cache.set("k", "v", ttl=0)
    await asyncio.sleep(0.02)
    assert await cache.get("k") is None
