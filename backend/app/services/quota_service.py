"""Subscription-tier quota enforcement.

A daily, per-(user, feature) counter checked against the user's plan. The counter
store is pluggable: ``RedisCounterStore`` (atomic, shared across replicas) in prod,
``InMemoryCounterStore`` in dev/tests. Enforcement is deterministic and unit-testable
independent of Redis.
"""
from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.core.exceptions import AppError
from app.domain.billing.plans import QuotaFeature, limit_for
from app.domain.identity.enums import SubscriptionPlan


class QuotaExceededError(AppError):
    status_code = 429
    code = "quota_exceeded"


@runtime_checkable
class CounterStore(Protocol):
    async def incr(self, key: str, ttl_seconds: int) -> int:
        """Increment ``key`` (creating it with ``ttl`` on first use) and return the value."""
        ...


class InMemoryCounterStore:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def incr(self, key: str, ttl_seconds: int) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]


class RedisCounterStore:
    def __init__(self, client) -> None:  # noqa: ANN001
        self._redis = client

    async def incr(self, key: str, ttl_seconds: int) -> int:
        value = await self._redis.incr(key)
        if value == 1:
            await self._redis.expire(key, ttl_seconds)
        return value


_DAY_SECONDS = 24 * 60 * 60


class QuotaService:
    def __init__(self, store: CounterStore, *, day: str = "global") -> None:
        self._store = store
        # ``day`` partitions counters so they reset daily (pass an ISO date in prod).
        self._day = day

    async def enforce(
        self, user_id: uuid.UUID, plan: SubscriptionPlan, feature: QuotaFeature
    ) -> int:
        """Increment usage; raise QuotaExceededError if the plan limit is reached.

        Returns the remaining allowance (or -1 for unlimited).
        """
        limit = limit_for(plan, feature)
        if limit < 0:
            return -1
        key = f"quota:{self._day}:{feature.value}:{user_id}"
        try:
            used = await self._store.incr(key, _DAY_SECONDS)
        except Exception:
            # Fail open: never block a user because the quota backend is down.
            return -1
        if used > limit:
            raise QuotaExceededError(
                f"Daily limit reached for '{feature.value}' on the {plan.value} plan "
                f"({limit}/day). Upgrade for more."
            )
        return max(0, limit - used)
