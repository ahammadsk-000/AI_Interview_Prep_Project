"""Unit tests for subscription-tier quota enforcement."""
from __future__ import annotations

import uuid

import pytest

from app.domain.billing.plans import QuotaFeature
from app.domain.identity.enums import SubscriptionPlan
from app.services.quota_service import (
    InMemoryCounterStore,
    QuotaExceededError,
    QuotaService,
)


@pytest.mark.asyncio
async def test_free_plan_blocks_after_limit():
    svc = QuotaService(InMemoryCounterStore(), day="2026-06-13")
    uid = uuid.uuid4()
    # FREE AI_INTERVIEW limit is 3.
    for _ in range(3):
        await svc.enforce(uid, SubscriptionPlan.FREE, QuotaFeature.AI_INTERVIEW)
    with pytest.raises(QuotaExceededError):
        await svc.enforce(uid, SubscriptionPlan.FREE, QuotaFeature.AI_INTERVIEW)


@pytest.mark.asyncio
async def test_remaining_decrements():
    svc = QuotaService(InMemoryCounterStore(), day="2026-06-13")
    uid = uuid.uuid4()
    r1 = await svc.enforce(uid, SubscriptionPlan.FREE, QuotaFeature.AGENT_WORKFLOW)  # limit 5
    r2 = await svc.enforce(uid, SubscriptionPlan.FREE, QuotaFeature.AGENT_WORKFLOW)
    assert r1 == 4 and r2 == 3


@pytest.mark.asyncio
async def test_pro_has_higher_limit_than_free():
    svc = QuotaService(InMemoryCounterStore(), day="2026-06-13")
    uid = uuid.uuid4()
    # PRO AI_INTERVIEW is 50 — 4 calls stay well under.
    for _ in range(4):
        remaining = await svc.enforce(uid, SubscriptionPlan.PRO, QuotaFeature.AI_INTERVIEW)
    assert remaining == 46


@pytest.mark.asyncio
async def test_enterprise_is_unlimited():
    svc = QuotaService(InMemoryCounterStore(), day="2026-06-13")
    uid = uuid.uuid4()
    for _ in range(100):
        assert await svc.enforce(uid, SubscriptionPlan.ENTERPRISE, QuotaFeature.AI_INTERVIEW) == -1


@pytest.mark.asyncio
async def test_separate_features_independent():
    svc = QuotaService(InMemoryCounterStore(), day="2026-06-13")
    uid = uuid.uuid4()
    for _ in range(3):
        await svc.enforce(uid, SubscriptionPlan.FREE, QuotaFeature.AI_INTERVIEW)
    # A different feature has its own counter.
    assert await svc.enforce(uid, SubscriptionPlan.FREE, QuotaFeature.AGENT_WORKFLOW) == 4
