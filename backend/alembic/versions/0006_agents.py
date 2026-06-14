"""multi-agent schema (agent_runs)

Revision ID: 0006_agents
Revises: 0005_evaluation
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_agents"
down_revision: Union[str, None] = "0005_evaluation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()
_json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("graph", sa.String(120), nullable=False),
        sa.Column("status", sa.Enum("running", "completed", "failed",
                                     name="agent_run_status", native_enum=False),
                  nullable=False, server_default="running"),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("inputs", _json),
        sa.Column("output", _json),
        sa.Column("steps", _json),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_trace_id", "agent_runs", ["trace_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
