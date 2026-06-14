"""Organization (multi-tenancy) + mentor dashboard endpoints (Phase 10)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.v1.deps import CurrentUser, OrgSvc
from app.schemas.organization import (
    AddMemberRequest,
    MemberPublic,
    MentorDashboard,
    OrgCreate,
    OrgPublic,
)

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.get("", response_model=list[OrgPublic])
async def list_my_orgs(current: CurrentUser, orgs: OrgSvc) -> list[OrgPublic]:
    rows = await orgs.list_my_orgs(current.id)
    return [
        OrgPublic(
            id=o.id, name=o.name, slug=o.slug, plan=o.plan, your_role=role, member_count=count
        )
        for o, role, count in rows
    ]


@router.post("", response_model=OrgPublic, status_code=status.HTTP_201_CREATED)
async def create_org(payload: OrgCreate, current: CurrentUser, orgs: OrgSvc) -> OrgPublic:
    org = await orgs.create(current.id, payload)
    _org, role, count = await orgs.get(org.id, current.id)
    return OrgPublic(
        id=org.id, name=org.name, slug=org.slug, plan=org.plan,
        your_role=role, member_count=count,
    )


@router.get("/{org_id}", response_model=OrgPublic)
async def get_org(org_id: uuid.UUID, current: CurrentUser, orgs: OrgSvc) -> OrgPublic:
    org, role, count = await orgs.get(org_id, current.id)
    return OrgPublic(
        id=org.id, name=org.name, slug=org.slug, plan=org.plan,
        your_role=role, member_count=count,
    )


@router.post("/{org_id}/members", response_model=MemberPublic, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: uuid.UUID, payload: AddMemberRequest, current: CurrentUser, orgs: OrgSvc
) -> MemberPublic:
    return await orgs.add_member(org_id, current.id, payload)


@router.get("/{org_id}/members", response_model=list[MemberPublic])
async def list_members(
    org_id: uuid.UUID, current: CurrentUser, orgs: OrgSvc
) -> list[MemberPublic]:
    return await orgs.list_members(org_id, current.id)


@router.get("/{org_id}/dashboard", response_model=MentorDashboard)
async def mentor_dashboard(
    org_id: uuid.UUID, current: CurrentUser, orgs: OrgSvc
) -> MentorDashboard:
    return await orgs.mentor_dashboard(org_id, current.id)
