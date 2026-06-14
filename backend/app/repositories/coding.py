"""SQLAlchemy repositories for the Coding context."""
from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coding import CodingChallenge, CodingSubmission, TestCase


class ChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, challenge: CodingChallenge) -> CodingChallenge:
        self._s.add(challenge)
        await self._s.flush()
        await self._s.refresh(challenge, attribute_names=["created_at", "updated_at"])
        return challenge

    async def get(self, id_: uuid.UUID) -> CodingChallenge | None:
        return await self._s.get(CodingChallenge, id_)

    async def get_by_slug(self, slug: str) -> CodingChallenge | None:
        stmt = select(CodingChallenge).where(CodingChallenge.slug == slug)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(CodingChallenge.id).where(CodingChallenge.slug == slug)
        return (await self._s.execute(stmt)).first() is not None

    async def list_visible(self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0):
        stmt = (
            select(CodingChallenge)
            .where(or_(CodingChallenge.is_public.is_(True),
                       CodingChallenge.created_by == user_id))
            .order_by(CodingChallenge.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def test_cases(self, challenge_id: uuid.UUID) -> list[TestCase]:
        stmt = (
            select(TestCase)
            .where(TestCase.challenge_id == challenge_id)
            .order_by(TestCase.order_idx)
        )
        return list((await self._s.execute(stmt)).scalars().all())


class SubmissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, submission: CodingSubmission) -> CodingSubmission:
        self._s.add(submission)
        await self._s.flush()
        await self._s.refresh(submission, attribute_names=["created_at", "updated_at"])
        return submission

    async def get(self, id_: uuid.UUID) -> CodingSubmission | None:
        return await self._s.get(CodingSubmission, id_)

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0):
        stmt = (
            select(CodingSubmission)
            .where(CodingSubmission.user_id == user_id)
            .order_by(CodingSubmission.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())
