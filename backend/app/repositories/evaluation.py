"""SQLAlchemy repositories for the Evaluation context."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import FeedbackReport, Score


class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, score: Score) -> Score:
        self._s.add(score)
        await self._s.flush()
        await self._s.refresh(score, attribute_names=["created_at", "updated_at"])
        return score

    async def get(self, id_: uuid.UUID) -> Score | None:
        return await self._s.get(Score, id_)

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0):
        stmt = (
            select(Score)
            .where(Score.user_id == user_id)
            .order_by(Score.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())


class FeedbackReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, report: FeedbackReport) -> FeedbackReport:
        self._s.add(report)
        await self._s.flush()
        await self._s.refresh(report, attribute_names=["created_at", "updated_at"])
        return report

    async def get(self, id_: uuid.UUID) -> FeedbackReport | None:
        return await self._s.get(FeedbackReport, id_)
