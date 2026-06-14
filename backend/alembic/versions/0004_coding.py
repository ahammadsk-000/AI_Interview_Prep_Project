"""coding / dsa schema

Revision ID: 0004_coding
Revises: 0003_interview_voice
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_coding"
down_revision: Union[str, None] = "0003_interview_voice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()
_json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


_DIFF = ("easy", "medium", "hard")
_LANG = ("python", "java", "javascript", "go", "cpp", "csharp")
_STATUS = ("pending", "accepted", "wrong_answer", "runtime_error",
           "compile_error", "time_limit", "unsupported")


def upgrade() -> None:
    op.create_table(
        "coding_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("difficulty", _enum("challenge_difficulty", *_DIFF), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("entrypoint", sa.String(120), nullable=False),
        sa.Column("starter_code", _json),
        sa.Column("tags", _json),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_coding_challenges_slug", "coding_challenges", ["slug"], unique=True)

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("challenge_id", sa.Uuid(),
                  sa.ForeignKey("coding_challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("args", _json),
        sa.Column("expected_output", _json),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_test_cases_challenge_id", "test_cases", ["challenge_id"])

    op.create_table(
        "coding_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("challenge_id", sa.Uuid(),
                  sa.ForeignKey("coding_challenges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", _enum("submission_language", *_LANG), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", _enum("submission_status", *_STATUS),
                  nullable=False, server_default="pending"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runtime_ms", sa.Float()),
        sa.Column("memory_kb", sa.Integer()),
        sa.Column("evaluation", _json),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_coding_submissions_user_id", "coding_submissions", ["user_id"])
    op.create_index("ix_coding_submissions_challenge_id", "coding_submissions",
                    ["challenge_id"])


def downgrade() -> None:
    op.drop_table("coding_submissions")
    op.drop_table("test_cases")
    op.drop_table("coding_challenges")
