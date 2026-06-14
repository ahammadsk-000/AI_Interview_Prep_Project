"""analytics schema (metric_snapshots)

Revision ID: 0007_analytics
Revises: 0006_agents
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_analytics"
down_revision: Union[str, None] = "0006_agents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=_now,
                  nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_metric_snapshots_user_id", "metric_snapshots", ["user_id"])
    op.create_index("ix_metric_snapshots_metric", "metric_snapshots", ["metric"])


def downgrade() -> None:
    op.drop_table("metric_snapshots")
