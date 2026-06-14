"""Organization use-cases: create org, manage members, mentor dashboard.

Multi-tenancy layer: an org groups users for team practice and gives mentors/admins
an aggregated readiness view of members (reusing the Phase-7 analytics engine).
Authorization is role-based within the org.
"""
from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.domain.organization.enums import ADMIN_ROLES, MANAGER_ROLES, OrgRole
from app.models.organization import Organization
from app.repositories.organization import OrgRepository
from app.repositories.user import UserRepository
from app.schemas.organization import (
    AddMemberRequest,
    MemberPublic,
    MemberReadiness,
    MentorDashboard,
    OrgCreate,
)
from app.services.analytics_service import AnalyticsService


class OrganizationService:
    def __init__(
        self, repo: OrgRepository, users: UserRepository, analytics: AnalyticsService
    ) -> None:
        self._repo = repo
        self._users = users
        self._analytics = analytics

    async def create(self, owner_id: uuid.UUID, data: OrgCreate) -> Organization:
        if await self._repo.slug_exists(data.slug):
            raise ConflictError(f"An organization with slug '{data.slug}' already exists.")
        org = await self._repo.add_org(
            Organization(name=data.name, slug=data.slug, owner_id=owner_id)
        )
        await self._repo.add_membership(org.id, owner_id, OrgRole.OWNER)
        return org

    async def _require_membership(self, org_id: uuid.UUID, user_id: uuid.UUID):
        org = await self._repo.get(org_id)
        membership = await self._repo.get_membership(org_id, user_id)
        if org is None or membership is None:
            raise NotFoundError("Organization not found.")
        return org, membership

    async def get(self, org_id: uuid.UUID, user_id: uuid.UUID):
        org, membership = await self._require_membership(org_id, user_id)
        count = await self._repo.member_count(org_id)
        return org, membership.role, count

    async def list_my_orgs(self, user_id: uuid.UUID):
        """Returns (org, role, member_count) for each org the user belongs to."""
        rows = await self._repo.list_for_user(user_id)
        out = []
        for org, role in rows:
            count = await self._repo.member_count(org.id)
            out.append((org, role, count))
        return out

    async def add_member(
        self, org_id: uuid.UUID, actor_id: uuid.UUID, data: AddMemberRequest
    ) -> MemberPublic:
        _org, membership = await self._require_membership(org_id, actor_id)
        if membership.role not in ADMIN_ROLES:
            raise PermissionDeniedError("Only org owners/admins can add members.")
        target = await self._users.get_by_email(data.email)
        if target is None:
            raise NotFoundError("No user with that email exists.")
        if await self._repo.get_membership(org_id, target.id) is not None:
            raise ConflictError("User is already a member of this organization.")
        await self._repo.add_membership(org_id, target.id, data.role)
        return MemberPublic(
            user_id=target.id, email=target.email, full_name=target.full_name, role=data.role
        )

    async def list_members(self, org_id: uuid.UUID, user_id: uuid.UUID) -> list[MemberPublic]:
        await self._require_membership(org_id, user_id)
        rows = await self._repo.list_members(org_id)
        return [
            MemberPublic(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role)
            for m, u in rows
        ]

    async def mentor_dashboard(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> MentorDashboard:
        _org, membership = await self._require_membership(org_id, user_id)
        if membership.role not in MANAGER_ROLES:
            raise PermissionDeniedError(
                "Only owners, admins, or mentors can view the org dashboard."
            )
        rows = await self._repo.list_members(org_id)
        members: list[MemberReadiness] = []
        readiness_values: list[int] = []
        for m, u in rows:
            overview = await self._analytics.overview(u.id)
            if overview.overall_readiness is not None:
                readiness_values.append(overview.overall_readiness)
            members.append(MemberReadiness(
                user_id=u.id, email=u.email, role=m.role,
                overall_readiness=overview.overall_readiness,
                interviews=overview.totals.get("interviews", 0),
                coding_submissions=overview.totals.get("coding_submissions", 0),
            ))
        avg = (round(sum(readiness_values) / len(readiness_values), 2)
               if readiness_values else None)
        return MentorDashboard(
            organization_id=org_id, member_count=len(members),
            average_readiness=avg, members=members,
        )
