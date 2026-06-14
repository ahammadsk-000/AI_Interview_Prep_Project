"""interview / voice schema

Revision ID: 0003_interview_voice
Revises: 0002_resume_ats
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_interview_voice"
down_revision: Union[str, None] = "0002_resume_ats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()
_json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


_TYPES = ("hr", "technical", "system_design", "ml", "genai", "devops", "pm")
_DIFF = ("easy", "medium", "hard")
_STATUS = ("active", "completed", "abandoned")
_ROLE = ("interviewer", "candidate")


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("type", _enum("interview_type", *_TYPES), nullable=False),
        sa.Column("difficulty", _enum("interview_difficulty", *_DIFF),
                  server_default="medium"),
        sa.Column("status", _enum("interview_status", *_STATUS),
                  nullable=False, server_default="active"),
        sa.Column("config", _json),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_interviews_user_id", "interviews", ["user_id"])

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("interview_id", sa.Uuid(),
                  sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_difficulty", _enum("session_difficulty", *_DIFF),
                  server_default="medium"),
        sa.Column("planned_questions", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("status", _enum("session_status", *_STATUS),
                  nullable=False, server_default="active"),
        sa.Column("avg_score", sa.Float()),
        sa.Column("summary", sa.Text()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_interview_sessions_interview_id", "interview_sessions",
                    ["interview_id"])

    op.create_table(
        "turns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(),
                  sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", _enum("turn_role", *_ROLE), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("order_idx", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer()),
        sa.Column("audio_key", sa.String(512)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_turns_session_id", "turns", ["session_id"])

    op.create_table(
        "voice_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("interview_session_id", sa.Uuid(),
                  sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", _enum("voice_session_status", "active", "ended"),
                  nullable=False, server_default="active"),
        sa.Column("provider", sa.String(64)),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_voice_sessions_interview_session_id", "voice_sessions",
                    ["interview_session_id"])

    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("voice_session_id", sa.Uuid(),
                  sa.ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("speaker", _enum("transcript_speaker", *_ROLE)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("order_idx", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_transcripts_voice_session_id", "transcripts", ["voice_session_id"])

    op.create_table(
        "recordings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("voice_session_id", sa.Uuid(),
                  sa.ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("speaker", _enum("recording_speaker", *_ROLE)),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("duration_ms", sa.Integer()),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_recordings_voice_session_id", "recordings", ["voice_session_id"])


def downgrade() -> None:
    op.drop_table("recordings")
    op.drop_table("transcripts")
    op.drop_table("voice_sessions")
    op.drop_table("turns")
    op.drop_table("interview_sessions")
    op.drop_table("interviews")
