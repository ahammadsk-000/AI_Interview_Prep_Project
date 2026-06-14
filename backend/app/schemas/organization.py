"""Organization / mentor-dashboard DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.domain.identity.enums import SubscriptionPlan
from app.domain.organization.enums import OrgRole


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9-]+$")


class OrgPublic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: SubscriptionPlan
    your_role: OrgRole
    member_count: int


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class MemberPublic(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str | None = None
    role: OrgRole


class MemberReadiness(BaseModel):
    user_id: uuid.UUID
    email: str
    role: OrgRole
    overall_readiness: int | None = None
    interviews: int = 0
    coding_submissions: int = 0


class MentorDashboard(BaseModel):
    organization_id: uuid.UUID
    member_count: int
    average_readiness: float | None = None
    members: list[MemberReadiness] = Field(default_factory=list)
