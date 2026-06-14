"""Multi-agent workflow endpoints (Module 11)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import AgentSvc, CurrentUser, require_quota
from app.domain.billing.plans import QuotaFeature
from app.models.agent import AgentRun
from app.schemas.agent import (
    AgentDescriptor,
    AgentRunPublic,
    AgentRunSummary,
    CareerReadinessRequest,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _to_public(run: AgentRun) -> AgentRunPublic:
    return AgentRunPublic(
        id=run.id, graph=run.graph, status=run.status.value, trace_id=run.trace_id,
        output=run.output or {}, steps=run.steps or [], tokens=run.tokens,
        latency_ms=run.latency_ms, created_at=run.created_at,
    )


@router.get("", response_model=list[AgentDescriptor])
async def list_agents(current: CurrentUser, agents: AgentSvc) -> list[AgentDescriptor]:
    return agents.list_agents()


@router.post(
    "/career-readiness",
    response_model=AgentRunPublic,
    dependencies=[Depends(require_quota(QuotaFeature.AGENT_WORKFLOW))],
)
async def run_career_readiness(
    payload: CareerReadinessRequest, current: CurrentUser, agents: AgentSvc
) -> AgentRunPublic:
    run = await agents.run_career_readiness(current.id, payload)
    return _to_public(run)


@router.get("/runs", response_model=list[AgentRunSummary])
async def list_runs(
    current: CurrentUser,
    agents: AgentSvc,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[AgentRunSummary]:
    records = await agents.list_runs(current.id, limit=limit, offset=offset)
    return [
        AgentRunSummary(
            id=r.id, graph=r.graph, status=r.status.value,
            overall_readiness=(r.output or {}).get("feedback", {}).get("overall_readiness"),
            tokens=r.tokens, created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/runs/{run_id}", response_model=AgentRunPublic)
async def get_run(
    run_id: uuid.UUID, current: CurrentUser, agents: AgentSvc
) -> AgentRunPublic:
    return _to_public(await agents.get_owned_run(run_id, current.id))
