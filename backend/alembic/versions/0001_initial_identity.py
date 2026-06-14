"""initial identity schema

Revision ID: 0001_identity
Revises:
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_identity"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", _enum("role_name", "ADMIN", "MENTOR", "RECRUITER", "USER"),
                  nullable=False, unique=True),
        sa.Column("description", sa.String(255)),
        _ts("created_at"),
        _ts("updated_at"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255)),
        sa.Column("full_name", sa.String(255)),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("target_role", sa.String(120)),
        sa.Column("experience_level",
                  _enum("experience_level", "fresher", "junior", "mid", "senior", "staff")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"),
                  primary_key=True),
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("provider", _enum("oauth_provider", "google", "github"), nullable=False),
        sa.Column("provider_account_id", sa.String(255), nullable=False),
        sa.Column("access_token", sa.Text()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("uq_oauth_provider_account", "oauth_accounts",
                    ["provider", "provider_account_id"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ip", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_refresh_token_hash", "sessions", ["refresh_token_hash"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("plan", _enum("subscription_plan", "free", "pro", "team", "enterprise"),
                  nullable=False, server_default="free"),
        sa.Column("status", _enum("subscription_status", "active", "past_due", "canceled"),
                  nullable=False, server_default="active"),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("seats", sa.Integer(), nullable=False, server_default="1"),
        _ts("created_at"),
        _ts("updated_at"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(120)),
        sa.Column("resource_id", sa.String(120)),
        sa.Column("ip", sa.String(64)),
        sa.Column("metadata", postgresql.JSONB().with_variant(sa.Text(), "sqlite")),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_audit_actor", "audit_logs", ["actor_user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")
    op.drop_table("sessions")
    op.drop_table("oauth_accounts")
    op.drop_table("user_roles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
