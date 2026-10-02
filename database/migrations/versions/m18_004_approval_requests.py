"""M18 approval requests.

Revision ID: m18_004_approval_requests
Revises: m8_003_daily_discoveries
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m18_004_approval_requests"
down_revision: str | None = "m8_003_daily_discoveries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("decision_note", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name="ck_approval_requests_status",
        ),
        sa.CheckConstraint(
            "action IN ('submit_application')",
            name="ck_approval_requests_action",
        ),
    )
    op.create_index("ix_approval_requests_user_id", "approval_requests", ["user_id"])
    op.create_index("ix_approval_requests_job_id", "approval_requests", ["job_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index(
        "uq_approval_requests_one_pending",
        "approval_requests",
        ["user_id", "job_id", "action"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_approval_requests_one_pending", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_job_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_user_id", table_name="approval_requests")
    op.drop_table("approval_requests")
