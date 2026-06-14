"""SQLAlchemy user & role repository."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.identity.enums import RoleName
from app.models.user import Role, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, id_: uuid.UUID) -> User | None:
        return await self._s.get(User, id_)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        stmt = select(func.count()).select_from(User).where(
            func.lower(User.email) == email.lower()
        )
        return bool((await self._s.execute(stmt)).scalar_one())

    async def add(self, user: User) -> User:
        self._s.add(user)
        await self._s.flush()
        # Refresh only server-generated columns; relationships were assigned in
        # memory and must not be expired (would trigger async lazy-load IO).
        await self._s.refresh(user, attribute_names=["created_at", "updated_at"])
        return user

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._s.execute(stmt)).scalars().all())

    async def get_role(self, name: RoleName) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def get_or_create_role(self, name: RoleName) -> Role:
        role = await self.get_role(name)
        if role is None:
            role = Role(name=name, description=f"{name.value} role")
            self._s.add(role)
            await self._s.flush()
        return role
