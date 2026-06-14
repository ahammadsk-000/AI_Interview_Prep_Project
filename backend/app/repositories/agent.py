"""SQLAlchemy repository for AgentRun."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentRun


class AgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, run: AgentRun) -> AgentRun:
        self._s.add(run)
        await self._s.flush()
        await self._s.refresh(run, attribute_names=["created_at", "updated_at"])
        return run

    async def get(self, id_: uuid.UUID) -> AgentRun | None:
        return await self._s.get(AgentRun, id_)

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0):
        stmt = (
            select(AgentRun)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())
