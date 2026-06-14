"""SQLAlchemy refresh-token session repository."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, record: Session) -> Session:
        self._s.add(record)
        await self._s.flush()
        await self._s.refresh(record)
        return record

    async def get_active_by_hash(self, token_hash: str) -> Session | None:
        stmt = select(Session).where(
            Session.refresh_token_hash == token_hash,
            Session.revoked_at.is_(None),
        )
        record = (await self._s.execute(stmt)).scalar_one_or_none()
        if record is None:
            return None
        expires = record.expires_at
        # SQLite returns naive datetimes; treat stored timestamps as UTC.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= datetime.now(UTC):
            return None
        return record

    async def revoke(self, session_id: uuid.UUID) -> None:
        await self._s.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._s.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
