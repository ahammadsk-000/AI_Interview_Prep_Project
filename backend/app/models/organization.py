"""Organization / multi-tenancy ORM models (Phase 10).

An ``Organization`` groups users for team practice and mentor dashboards. Membership
is many-to-many with a per-org role. This is additive: individual user-scoped
resources continue to work unchanged; org-level features layer on top.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, uuid_pk
from app.domain.identity.enums import SubscriptionPlan
from app.domain.organization.enums import OrgRole
from app.models.user import _enum


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    plan: Mapped[SubscriptionPlan] = mapped_column(
        _enum(SubscriptionPlan, "org_plan"), default=SubscriptionPlan.TEAM, nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        Index("uq_org_member", "organization_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[OrgRole] = mapped_column(
        _enum(OrgRole, "org_role"), default=OrgRole.MEMBER, nullable=False
    )

    organization: Mapped[Organization] = relationship(back_populates="memberships")
