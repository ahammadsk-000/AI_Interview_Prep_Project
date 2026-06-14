"""Identity & Access ORM models.

Persistence representation of the Identity bounded context. Types are chosen to
be portable across PostgreSQL (production) and SQLite (tests): ``Uuid`` renders
natively on PG and as CHAR on SQLite; enums use non-native string columns.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, uuid_pk
from app.domain.identity.enums import (
    ExperienceLevel,
    OAuthProvider,
    RoleName,
    SubscriptionPlan,
    SubscriptionStatus,
)

# Generic JSON everywhere (serializes dict/list, works on SQLite); JSONB on Postgres.
JsonType = JSON().with_variant(JSONB, "postgresql")


def _enum(py_enum: type, name: str) -> SAEnum:
    """Portable string-backed enum column type."""
    return SAEnum(py_enum, name=name, native_enum=False, validate_strings=True)


# ── Association: users <-> roles ────────────────────────────────────
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[RoleName] = mapped_column(_enum(RoleName, "role_name"), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    users: Mapped[list[User]] = relationship(
        secondary=user_roles, back_populates="roles", lazy="selectin"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255))  # null => OAuth-only
    full_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    target_role: Mapped[str | None] = mapped_column(String(120))
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(
        _enum(ExperienceLevel, "experience_level")
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users", lazy="selectin"
    )
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )

    @property
    def role_names(self) -> set[RoleName]:
        return {r.name for r in self.roles}

    def has_role(self, role: RoleName) -> bool:
        return role in self.role_names


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        Index("uq_oauth_provider_account", "provider", "provider_account_id", unique=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[OAuthProvider] = mapped_column(_enum(OAuthProvider, "oauth_provider"))
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text)  # encrypted at rest in prod

    user: Mapped[User] = relationship(back_populates="oauth_accounts")


class Session(Base):
    """Refresh-token session record (rotation + revocation)."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        _enum(SubscriptionPlan, "subscription_plan"),
        default=SubscriptionPlan.FREE,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        _enum(SubscriptionStatus, "subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seats: Mapped[int] = mapped_column(default=1, nullable=False)

    user: Mapped[User] = relationship(back_populates="subscription")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_actor", "actor_user_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(120))
    ip: Mapped[str | None] = mapped_column(String(64))
    meta: Mapped[dict | None] = mapped_column("metadata", JsonType)
