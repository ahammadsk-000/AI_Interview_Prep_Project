"""resume / job / ats schema

Revision ID: 0002_resume_ats
Revises: 0001_identity
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_resume_ats"
down_revision: Union[str, None] = "0001_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.func.now()
_json = postgresql.JSONB().with_variant(sa.Text(), "sqlite")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def _ts(col: str) -> sa.Column:
    return sa.Column(col, sa.DateTime(timezone=True), server_default=_now, nullable=False)


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("mime", sa.String(120), nullable=False),
        sa.Column("parsed_text", sa.Text()),
        sa.Column("status",
                  _enum("resume_status", "uploaded", "parsing", "parsed", "failed"),
                  nullable=False, server_default="uploaded"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("resume_id", sa.Uuid(), sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content", _json),
        sa.Column("source", _enum("resume_source", "upload", "ai_rewrite"),
                  nullable=False, server_default="upload"),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_resume_versions_resume_id", "resume_versions", ["resume_id"])

    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("company", sa.String(255)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("extracted_skills", _json),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_job_descriptions_user_id", "job_descriptions", ["user_id"])

    op.create_table(
        "ats_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("resume_id", sa.Uuid(), sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("job_description_id", sa.Uuid(),
                  sa.ForeignKey("job_descriptions.id", ondelete="SET NULL")),
        sa.Column("ats_score", sa.Integer(), nullable=False),
        sa.Column("recruiter_score", sa.Integer(), nullable=False),
        sa.Column("tech_score", sa.Integer(), nullable=False),
        sa.Column("comm_score", sa.Integer(), nullable=False),
        sa.Column("matched_keywords", _json),
        sa.Column("missing_keywords", _json),
        sa.Column("suggestions", _json),
        sa.Column("breakdown", _json),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_ats_reports_resume_id", "ats_reports", ["resume_id"])
    op.create_index("ix_ats_reports_job_description_id", "ats_reports", ["job_description_id"])


def downgrade() -> None:
    op.drop_table("ats_reports")
    op.drop_table("job_descriptions")
    op.drop_table("resume_versions")
    op.drop_table("resumes")
