"""M8 daily job discovery results.

Revision ID: m8_003_daily_discoveries
Revises: m6_002_profiles_resumes
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m8_003_daily_discoveries"
down_revision: str | None = "m6_002_profiles_resumes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_discoveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_on", sa.Date(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("selection_limit", sa.Integer(), nullable=False),
        sa.Column("considered", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Integer(), nullable=False),
        sa.Column("selections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_failures", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "run_on", name="uq_daily_discoveries_user_run"),
        sa.CheckConstraint("threshold BETWEEN 0 AND 100", name="ck_daily_discoveries_threshold"),
        sa.CheckConstraint(
            "selection_limit BETWEEN 1 AND 20",
            name="ck_daily_discoveries_selection_limit",
        ),
        sa.CheckConstraint("considered >= 0", name="ck_daily_discoveries_considered"),
        sa.CheckConstraint(
            "rejected >= 0 AND rejected <= considered",
            name="ck_daily_discoveries_rejected",
        ),
    )
    op.create_index("ix_daily_discoveries_user_id", "daily_discoveries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_daily_discoveries_user_id", table_name="daily_discoveries")
    op.drop_table("daily_discoveries")
