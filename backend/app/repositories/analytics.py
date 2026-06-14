"""Read-side analytics queries across the platform's tables (per user).

Returns lightweight rows; trend bucketing/summaries happen in the pure
``domain.analytics.aggregations`` layer (portable + testable).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evaluation.enums import SubjectType
from app.models.agent import AgentRun
from app.models.analytics import MetricSnapshot
from app.models.coding import CodingSubmission
from app.models.evaluation import Score
from app.models.interview import Interview, InterviewSession
from app.models.resume import AtsReport, Resume


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _count(self, stmt) -> int:
        return int((await self._s.execute(stmt)).scalar_one())

    async def counts(self, user_id: uuid.UUID) -> dict[str, int]:
        interviews = await self._count(
            select(func.count()).select_from(Interview).where(Interview.user_id == user_id)
        )
        answers = await self._count(
            select(func.count()).select_from(Score)
            .where(Score.user_id == user_id, Score.subject_type == SubjectType.ANSWER)
        )
        behavioral = await self._count(
            select(func.count()).select_from(Score)
            .where(Score.user_id == user_id, Score.subject_type == SubjectType.BEHAVIORAL)
        )
        coding = await self._count(
            select(func.count()).select_from(CodingSubmission)
            .where(CodingSubmission.user_id == user_id)
        )
        resumes = await self._count(
            select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
        )
        agent_runs = await self._count(
            select(func.count()).select_from(AgentRun).where(AgentRun.user_id == user_id)
        )
        return {
            "interviews": interviews, "answers_graded": answers,
            "behavioral_graded": behavioral, "coding_submissions": coding,
            "resumes": resumes, "agent_runs": agent_runs,
        }

    async def score_rows(self, user_id: uuid.UUID, subject_type: SubjectType):
        stmt = (
            select(Score.created_at, Score.total, Score.breakdown, Score.question)
            .where(Score.user_id == user_id, Score.subject_type == subject_type)
            .order_by(Score.created_at)
        )
        return (await self._s.execute(stmt)).all()

    async def coding_rows(self, user_id: uuid.UUID):
        stmt = (
            select(CodingSubmission.created_at, CodingSubmission.status,
                   CodingSubmission.evaluation)
            .where(CodingSubmission.user_id == user_id)
            .order_by(CodingSubmission.created_at)
        )
        return (await self._s.execute(stmt)).all()

    async def ats_rows(self, user_id: uuid.UUID):
        stmt = (
            select(AtsReport.created_at, AtsReport.ats_score)
            .join(Resume, AtsReport.resume_id == Resume.id)
            .where(Resume.user_id == user_id)
            .order_by(AtsReport.created_at)
        )
        return (await self._s.execute(stmt)).all()

    async def interview_rows(self, user_id: uuid.UUID):
        stmt = (
            select(InterviewSession.created_at, InterviewSession.status,
                   InterviewSession.avg_score, Interview.type)
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .where(Interview.user_id == user_id)
            .order_by(InterviewSession.created_at.desc())
        )
        return (await self._s.execute(stmt)).all()

    async def snapshot_rows(self, user_id: uuid.UUID, metric: str):
        stmt = (
            select(MetricSnapshot.captured_at, MetricSnapshot.value)
            .where(MetricSnapshot.user_id == user_id, MetricSnapshot.metric == metric)
            .order_by(MetricSnapshot.captured_at)
        )
        return (await self._s.execute(stmt)).all()

    async def latest_agent_readiness(self, user_id: uuid.UUID) -> int | None:
        stmt = (
            select(AgentRun.output)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        row = (await self._s.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        return (row.get("feedback") or {}).get("overall_readiness")

    async def add_snapshot(
        self, user_id: uuid.UUID, *, metric: str, value: float,
        captured_at: datetime | None = None,
    ) -> MetricSnapshot:
        snap = MetricSnapshot(user_id=user_id, metric=metric, value=value)
        if captured_at is not None:
            snap.captured_at = captured_at
        self._s.add(snap)
        await self._s.flush()
        await self._s.refresh(snap, attribute_names=["created_at", "updated_at"])
        return snap
