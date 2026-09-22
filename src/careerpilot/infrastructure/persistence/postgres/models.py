from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from careerpilot.infrastructure.persistence.postgres.base import Base


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_jobs_status"),
        CheckConstraint(
            "remote_policy IN ('unspecified', 'onsite', 'remote', 'hybrid')",
            name="ck_jobs_remote_policy",
        ),
        CheckConstraint(
            "employment_type IN ("
            "'unspecified', 'full_time', 'part_time', 'contract', 'internship', 'temporary'"
            ")",
            name="ck_jobs_employment_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(63), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    extra: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class CareerProfileModel(Base):
    __tablename__ = "career_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_career_profiles_user_id"),
        CheckConstraint(
            "remote_policy IN ('unspecified', 'onsite', 'remote', 'hybrid')",
            name="ck_career_profiles_remote_policy",
        ),
        CheckConstraint(
            "employment_type IN ("
            "'unspecified', 'full_time', 'part_time', 'contract', 'internship', 'temporary'"
            ")",
            name="ck_career_profiles_employment_type",
        ),
        CheckConstraint(
            "years_experience IS NULL OR (years_experience >= 0 AND years_experience <= 60)",
            name="ck_career_profiles_years_experience",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    target_titles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    locations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    remote_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResumeModel(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_resumes_user_id_version"),
        CheckConstraint("version >= 1", name="ck_resumes_version"),
        CheckConstraint("content_type IN ('text/plain')", name="ck_resumes_content_type"),
        Index(
            "uq_resumes_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
