"""User-facing Pydantic DTOs (never expose ORM models / password hashes)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.identity.enums import ExperienceLevel, RoleName, SubscriptionPlan


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    target_role: str | None = Field(default=None, max_length=120)
    experience_level: ExperienceLevel | None = None


class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    avatar_url: str | None = None
    is_active: bool
    is_verified: bool
    roles: list[RoleName] = Field(default_factory=list)
    plan: SubscriptionPlan | None = None
    created_at: datetime

    @classmethod
    def from_orm_user(cls, user) -> UserPublic:  # noqa: ANN001
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            target_role=user.target_role,
            experience_level=user.experience_level,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=sorted(user.role_names, key=lambda r: r.value),
            plan=user.subscription.plan if user.subscription else None,
            created_at=user.created_at,
        )


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)
    target_role: str | None = Field(default=None, max_length=120)
    experience_level: ExperienceLevel | None = None
