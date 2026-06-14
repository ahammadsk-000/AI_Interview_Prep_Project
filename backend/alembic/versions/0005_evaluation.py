"""evaluation schema (scores + feedback reports)

Revision ID: 0005_evaluation
Revises: 0004_coding
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_evaluation"
down_revision: Union[str, None] = "0004_coding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()
_json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("subject_type",
                  _enum("score_subject_type", "answer", "behavioral", "coding", "resume"),
                  nullable=False),
        sa.Column("subject_id", sa.Uuid()),
        sa.Column("question", sa.Text()),
        sa.Column("answer", sa.Text()),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("breakdown", _json),
        sa.Column("feedback", _json),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_scores_user_id", "scores", ["user_id"])
    op.create_index("ix_scores_subject_id", "scores", ["subject_id"])

    op.create_table(
        "feedback_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("interview_session_id", sa.Uuid()),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("strengths", _json),
        sa.Column("improvements", _json),
        sa.Column("detail", _json),
        sa.Column("pdf_key", sa.String(512)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_feedback_reports_user_id", "feedback_reports", ["user_id"])
    op.create_index("ix_feedback_reports_session", "feedback_reports",
                    ["interview_session_id"])


def downgrade() -> None:
    op.drop_table("feedback_reports")
    op.drop_table("scores")
