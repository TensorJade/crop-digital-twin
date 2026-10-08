"""Identity SQL tables, with explicit logical references and no credential-bearing audit."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from crop_twin.infrastructure.database.models import Base as Base


class OrganizationRecord(Base):
    """One tenant scope, independent of its display name."""

    __tablename__ = "organizations"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserRecord(Base):
    """One active/inactive account; role changes are not exposed in M2."""

    __tablename__ = "users"
    __table_args__ = (
        Index("uniq_users_username", "username", unique=True),
        Index("idx_users_organization_id", "organization_id", "created_at", "id"),
        CheckConstraint("role IN ('owner', 'operator', 'viewer')", name="ck_users_role"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    username: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SessionRecord(Base):
    """Random session digest and session-bound CSRF token."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("uniq_user_sessions_token_digest", "token_digest", unique=True),
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_expires_at", "expires_at"),
        CheckConstraint("expires_at > created_at", name="ck_user_sessions_dates"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid)
    token_digest: Mapped[str] = mapped_column(String(64))
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginLimitRecord(Base):
    """Per direct-source failure window; no raw IP, username or password is stored."""

    __tablename__ = "login_limits"
    __table_args__ = (
        Index("uniq_login_limits_source_key", "source_key", unique=True),
        CheckConstraint("failures BETWEEN 0 AND 5", name="ck_login_limits_failures"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64))
    failures: Mapped[int] = mapped_column(Integer)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditRecord(Base):
    """Same-transaction append-only metadata for a team's operations."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("idx_audit_events_organization_id", "organization_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(Uuid)
    actor_user_id: Mapped[UUID] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
