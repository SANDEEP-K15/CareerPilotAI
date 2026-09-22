"""M6 career profiles and versioned resumes.

Revision ID: m6_002_profiles_resumes
Revises: m1_001_users_jobs
Create Date: 2026-09-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m6_002_profiles_resumes"
down_revision: str | None = "m1_001_users_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("headline", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_titles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("remote_policy", sa.String(length=32), nullable=False),
        sa.Column("employment_type", sa.String(length=32), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_career_profiles_user_id"),
        sa.CheckConstraint(
            "remote_policy IN ('unspecified', 'onsite', 'remote', 'hybrid')",
            name="ck_career_profiles_remote_policy",
        ),
        sa.CheckConstraint(
            "employment_type IN ("
            "'unspecified', 'full_time', 'part_time', 'contract', 'internship', 'temporary'"
            ")",
            name="ck_career_profiles_employment_type",
        ),
        sa.CheckConstraint(
            "years_experience IS NULL OR (years_experience >= 0 AND years_experience <= 60)",
            name="ck_career_profiles_years_experience",
        ),
    )

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "version", name="uq_resumes_user_id_version"),
        sa.CheckConstraint("version >= 1", name="ck_resumes_version"),
        sa.CheckConstraint("content_type IN ('text/plain')", name="ck_resumes_content_type"),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_index(
        "uq_resumes_one_active_per_user",
        "resumes",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_resumes_one_active_per_user", table_name="resumes")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")
    op.drop_table("career_profiles")
