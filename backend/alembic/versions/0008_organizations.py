"""organizations (multi-tenancy)

Revision ID: 0008_organizations
Revises: 0007_analytics
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_organizations"
down_revision: Union[str, None] = "0007_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


_PLAN = ("free", "pro", "team", "enterprise")
_ORG_ROLE = ("owner", "admin", "mentor", "member")


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("plan", _enum("org_plan", *_PLAN), nullable=False, server_default="team"),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"),
                  nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("role", _enum("org_role", *_ORG_ROLE), nullable=False,
                  server_default="member"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_org_memberships_org", "organization_memberships",
                    ["organization_id"])
    op.create_index("ix_org_memberships_user", "organization_memberships", ["user_id"])
    op.create_index("uq_org_member", "organization_memberships",
                    ["organization_id", "user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
