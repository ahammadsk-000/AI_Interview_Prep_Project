"""Analytics dashboard use-cases.

Composes the read-side repository with the pure aggregation helpers to produce the
dashboard overview, metric trends, activity history, and metric snapshots.
"""
from __future__ import annotations

import uuid

from app.core.cache import Cache
from app.core.config import settings
from app.domain.analytics.aggregations import (
    Summary,
    average_dimensions,
    bucket_series,
    summarize,
)
from app.domain.analytics.enums import Bucket, HistoryKind, MetricName
from app.domain.evaluation.enums import SubjectType
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    AtsStats,
    CodingStats,
    DashboardOverview,
    HistoryItem,
    InterviewStats,
)


def _val(enum_or_str) -> str:
    return getattr(enum_or_str, "value", enum_or_str)


class AnalyticsService:
    def __init__(
        self,
        repo: AnalyticsRepository,
        cache: Cache | None = None,
        write_repo: AnalyticsRepository | None = None,
    ) -> None:
        # Reads use ``repo`` (may be a read replica); writes (snapshots) use the
        # primary via ``write_repo`` (falls back to ``repo`` when not split).
        self._repo = repo
        self._cache = cache
        self._write_repo = write_repo or repo

    # ── Overview ─────────────────────────────────────────────────────
    async def overview(self, user_id: uuid.UUID) -> DashboardOverview:
        key = f"analytics:overview:{user_id}"
        if self._cache is not None:
            cached = await self._cache.get(key)
            if cached is not None:
                return DashboardOverview.model_validate(cached)

        result = await self._compute_overview(user_id)
        if self._cache is not None:
            await self._cache.set(key, result.model_dump(mode="json"),
                                  settings.CACHE_TTL_SECONDS)
        return result

    async def _compute_overview(self, user_id: uuid.UUID) -> DashboardOverview:
        counts = await self._repo.counts(user_id)

        answer_rows = await self._repo.score_rows(user_id, SubjectType.ANSWER)
        dims = average_dimensions([r.breakdown for r in answer_rows])

        coding = await self._coding_stats(user_id)
        ats = await self._ats_stats(user_id)
        interviews = await self._interview_stats(user_id)

        overall = await self._repo.latest_agent_readiness(user_id)
        if overall is None:
            overall = self._composite_readiness(dims.averages, coding, ats, interviews)

        return DashboardOverview(
            totals=counts,
            overall_readiness=overall,
            dimension_averages=dims.averages,
            coding=coding,
            ats=ats,
            interviews=interviews,
        )

    async def _coding_stats(self, user_id: uuid.UUID) -> CodingStats:
        rows = await self._repo.coding_rows(user_id)
        readiness = [
            (r.evaluation or {}).get("readiness_score")
            for r in rows if (r.evaluation or {}).get("readiness_score") is not None
        ]
        accepted = sum(1 for r in rows if _val(r.status) == "accepted")
        total = len(rows)
        return CodingStats(
            submissions=total,
            accepted=accepted,
            acceptance_rate=round(accepted / total, 2) if total else 0.0,
            avg_readiness=round(sum(readiness) / len(readiness), 2) if readiness else 0.0,
            best_readiness=max(readiness) if readiness else 0,
        )

    async def _ats_stats(self, user_id: uuid.UUID) -> AtsStats:
        rows = await self._repo.ats_rows(user_id)
        scores = [r.ats_score for r in rows]
        return AtsStats(
            reports=len(scores),
            latest_score=scores[-1] if scores else None,
            best_score=max(scores) if scores else None,
            improvement_delta=round(scores[-1] - scores[0], 2) if len(scores) >= 2 else 0.0,
        )

    async def _interview_stats(self, user_id: uuid.UUID) -> InterviewStats:
        rows = await self._repo.interview_rows(user_id)
        completed = sum(1 for r in rows if _val(r.status) == "completed")
        avgs = [r.avg_score for r in rows if r.avg_score is not None]
        return InterviewStats(
            total=len(rows),
            completed=completed,
            avg_score=round(sum(avgs) / len(avgs), 2) if avgs else None,
        )

    @staticmethod
    def _composite_readiness(dims, coding, ats, interviews) -> int | None:
        parts: list[float] = []
        if dims:
            parts.append(sum(dims.values()) / len(dims))
        if coding.submissions:
            parts.append(coding.avg_readiness)
        if ats.latest_score is not None:
            parts.append(ats.latest_score)
        if interviews.avg_score is not None:
            parts.append(interviews.avg_score)
        return round(sum(parts) / len(parts)) if parts else None

    # ── Trends ───────────────────────────────────────────────────────
    async def trend(self, user_id: uuid.UUID, metric: MetricName, bucket: Bucket):
        points = await self._series(user_id, metric)
        buckets = bucket_series(points, bucket)
        summary = summarize([v for _ts, v in points])
        return buckets, summary

    async def _series(self, user_id: uuid.UUID, metric: MetricName):
        if metric == MetricName.READINESS:
            rows = await self._repo.snapshot_rows(user_id, MetricName.READINESS.value)
            return [(r.captured_at, float(r.value)) for r in rows]
        if metric == MetricName.ATS:
            rows = await self._repo.ats_rows(user_id)
            return [(r.created_at, float(r.ats_score)) for r in rows]
        if metric == MetricName.CODING:
            rows = await self._repo.coding_rows(user_id)
            return [
                (r.created_at, float((r.evaluation or {})["readiness_score"]))
                for r in rows if (r.evaluation or {}).get("readiness_score") is not None
            ]
        # COMMUNICATION / TECHNICAL → answer-score dimensions
        rows = await self._repo.score_rows(user_id, SubjectType.ANSWER)
        dim = metric.value
        out = []
        for r in rows:
            v = (r.breakdown or {}).get("dimensions", {}).get(dim)
            if v is not None:
                out.append((r.created_at, float(v)))
        return out

    # ── History ──────────────────────────────────────────────────────
    async def history(
        self, user_id: uuid.UUID, kind: HistoryKind, limit: int = 20
    ) -> list[HistoryItem]:
        items: list[HistoryItem] = []
        if kind == HistoryKind.INTERVIEW:
            for r in await self._repo.interview_rows(user_id):
                items.append(HistoryItem(
                    kind=kind, label=f"{_val(r.type)} interview", score=r.avg_score,
                    status=_val(r.status), occurred_at=r.created_at))
        elif kind in (HistoryKind.ANSWER, HistoryKind.BEHAVIORAL):
            subject = (SubjectType.ANSWER if kind == HistoryKind.ANSWER
                       else SubjectType.BEHAVIORAL)
            for r in reversed(await self._repo.score_rows(user_id, subject)):
                items.append(HistoryItem(
                    kind=kind, label=(r.question or kind.value.title()), score=r.total,
                    occurred_at=r.created_at))
        elif kind == HistoryKind.CODING:
            for r in reversed(await self._repo.coding_rows(user_id)):
                items.append(HistoryItem(
                    kind=kind, label="Coding submission",
                    score=(r.evaluation or {}).get("readiness_score"),
                    status=_val(r.status), occurred_at=r.created_at))
        elif kind == HistoryKind.ATS:
            for r in reversed(await self._repo.ats_rows(user_id)):
                items.append(HistoryItem(
                    kind=kind, label="ATS report", score=r.ats_score,
                    occurred_at=r.created_at))
        items.sort(key=lambda i: i.occurred_at, reverse=True)
        return items[:limit]

    # ── Snapshots ────────────────────────────────────────────────────
    async def capture_snapshot(
        self, user_id: uuid.UUID, metric: MetricName, value: float | None
    ):
        if value is None:
            overview = await self.overview(user_id)
            value = float(overview.overall_readiness or 0)
        return await self._write_repo.add_snapshot(user_id, metric=metric.value, value=value)

    @staticmethod
    def to_summary_dict(summary: Summary) -> dict:
        return {
            "count": summary.count, "average": summary.average,
            "minimum": summary.minimum, "maximum": summary.maximum,
            "first": summary.first, "latest": summary.latest,
            "delta": summary.delta, "direction": summary.direction,
        }
