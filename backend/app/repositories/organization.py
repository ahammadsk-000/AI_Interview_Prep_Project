"""SQLAlchemy repository for organizations + memberships."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.organization.enums import OrgRole
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User


class OrgRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_org(self, org: Organization) -> Organization:
        self._s.add(org)
        await self._s.flush()
        await self._s.refresh(org, attribute_names=["created_at", "updated_at"])
        return org

    async def get(self, id_: uuid.UUID) -> Organization | None:
        return await self._s.get(Organization, id_)

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(Organization.id).where(Organization.slug == slug)
        return (await self._s.execute(stmt)).first() is not None

    async def add_membership(
        self, org_id: uuid.UUID, user_id: uuid.UUID, role: OrgRole
    ) -> OrganizationMembership:
        m = OrganizationMembership(organization_id=org_id, user_id=user_id, role=role)
        self._s.add(m)
        await self._s.flush()
        return m

    async def get_membership(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMembership | None:
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
        return (await self._s.execute(stmt)).scalar_one_or_none()

    async def member_count(self, org_id: uuid.UUID) -> int:
        stmt = (
            select(func.count()).select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == org_id)
        )
        return int((await self._s.execute(stmt)).scalar_one())

    async def list_members(self, org_id: uuid.UUID):
        """Returns (membership, user) rows."""
        stmt = (
            select(OrganizationMembership, User)
            .join(User, OrganizationMembership.user_id == User.id)
            .where(OrganizationMembership.organization_id == org_id)
            .order_by(OrganizationMembership.created_at)
        )
        return (await self._s.execute(stmt)).all()

    async def list_for_user(self, user_id: uuid.UUID):
        """Returns (organization, role) rows for every org the user belongs to."""
        stmt = (
            select(Organization, OrganizationMembership.role)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Organization.id,
            )
            .where(OrganizationMembership.user_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        return (await self._s.execute(stmt)).all()
