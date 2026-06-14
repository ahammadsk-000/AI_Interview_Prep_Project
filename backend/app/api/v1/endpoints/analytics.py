"""Analytics Dashboard endpoints (Module 13)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.v1.deps import AnalyticsSvc, CurrentUser
from app.domain.analytics.enums import Bucket, HistoryKind, MetricName
from app.schemas.analytics import (
    DashboardOverview,
    HistoryItem,
    SnapshotRequest,
    SummaryPublic,
    TrendPointPublic,
    TrendResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=DashboardOverview)
async def overview(current: CurrentUser, analytics: AnalyticsSvc) -> DashboardOverview:
    return await analytics.overview(current.id)


@router.get("/trends", response_model=TrendResponse)
async def trends(
    current: CurrentUser,
    analytics: AnalyticsSvc,
    metric: MetricName = Query(MetricName.READINESS),
    bucket: Bucket = Query(Bucket.DAY),
) -> TrendResponse:
    points, summary = await analytics.trend(current.id, metric, bucket)
    return TrendResponse(
        metric=metric,
        bucket=bucket,
        points=[TrendPointPublic(period=p.period, value=p.value, count=p.count) for p in points],
        summary=SummaryPublic(**analytics.to_summary_dict(summary)),
    )


@router.get("/history", response_model=list[HistoryItem])
async def history(
    current: CurrentUser,
    analytics: AnalyticsSvc,
    kind: HistoryKind = Query(HistoryKind.INTERVIEW),
    limit: int = Query(20, ge=1, le=100),
) -> list[HistoryItem]:
    return await analytics.history(current.id, kind, limit=limit)


@router.post("/snapshots", response_model=dict)
async def capture_snapshot(
    payload: SnapshotRequest, current: CurrentUser, analytics: AnalyticsSvc
) -> dict:
    snap = await analytics.capture_snapshot(current.id, payload.metric, payload.value)
    return {"id": str(snap.id), "metric": snap.metric, "value": snap.value,
            "captured_at": snap.captured_at.isoformat()}
