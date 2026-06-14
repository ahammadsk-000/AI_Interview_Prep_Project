"""Analytics dashboard DTOs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.analytics.enums import Bucket, HistoryKind, MetricName


class TrendPointPublic(BaseModel):
    period: str
    value: float
    count: int


class SummaryPublic(BaseModel):
    count: int
    average: float
    minimum: float
    maximum: float
    first: float | None = None
    latest: float | None = None
    delta: float
    direction: str


class CodingStats(BaseModel):
    submissions: int
    accepted: int
    acceptance_rate: float
    avg_readiness: float
    best_readiness: int


class AtsStats(BaseModel):
    reports: int
    latest_score: int | None = None
    best_score: int | None = None
    improvement_delta: float = 0.0


class InterviewStats(BaseModel):
    total: int
    completed: int
    avg_score: float | None = None


class DashboardOverview(BaseModel):
    totals: dict[str, int]
    overall_readiness: int | None = None
    dimension_averages: dict[str, int] = Field(default_factory=dict)
    coding: CodingStats
    ats: AtsStats
    interviews: InterviewStats


class TrendResponse(BaseModel):
    metric: MetricName
    bucket: Bucket
    points: list[TrendPointPublic] = Field(default_factory=list)
    summary: SummaryPublic


class HistoryItem(BaseModel):
    kind: HistoryKind
    label: str
    score: float | None = None
    status: str | None = None
    occurred_at: datetime


class SnapshotRequest(BaseModel):
    metric: MetricName = MetricName.READINESS
    value: float | None = None  # if omitted, the service computes current readiness
