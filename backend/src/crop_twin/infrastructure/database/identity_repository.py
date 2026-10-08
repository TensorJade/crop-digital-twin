"""SQL identity adapter shared by SQLite and PostgreSQL."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session as SqlSession

from crop_twin.domain.identity.models import AuditEvent, Organization, Role, Session, User
from crop_twin.domain.pagination import Page
from crop_twin.infrastructure.database.identity_models import (
    AuditRecord,
    LoginLimitRecord,
    OrganizationRecord,
    SessionRecord,
    UserRecord,
)
from crop_twin.infrastructure.database.models import PlotRecord


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _user(record: UserRecord) -> User:
    return User(
        record.id,
        record.organization_id,
        record.username,
        record.display_name,
        cast(Role, record.role),
        record.is_active,
        _utc(record.created_at),
        record.password_hash,
    )


class SqlIdentityRepository:
    """Queries and mutations use a caller-owned transaction, including audit records."""

    def __init__(self, session: SqlSession) -> None:
        self.session = session

    def add_organization(self, organization: Organization) -> None:
        """Persist the team before inserting its logical children."""
        self.session.add(OrganizationRecord(**asdict(organization)))
        self.session.flush()

    def get_organization(self, organization_id: UUID) -> Organization | None:
        """Read one organization fact."""
        record = self.session.get(OrganizationRecord, organization_id)
        return Organization(record.id, record.name, _utc(record.created_at)) if record else None

    def get_user(self, user_id: UUID, *, lock: bool = False) -> User | None:
        """Lock accounts before a write to serialize deactivation with farm operations."""
        statement = select(UserRecord).where(UserRecord.id == user_id)
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        record = self.session.scalar(statement)
        return _user(record) if record else None

    def find_user(self, username: str, *, lock: bool = False) -> User | None:
        """Look up the canonical login name, with uniform absence handling in the service."""
        statement = select(UserRecord).where(UserRecord.username == username)
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        record = self.session.scalar(statement)
        return _user(record) if record else None

    def add_user(self, user: User) -> None:
        """Insert an already validated account and hash."""
        self.session.add(UserRecord(**asdict(user)))
        self.session.flush()

    def list_users(self, organization_id: UUID, limit: int, offset: int) -> Page[User]:
        """Page a single organization's accounts."""
        condition = UserRecord.organization_id == organization_id
        total = (
            self.session.scalar(select(func.count()).select_from(UserRecord).where(condition)) or 0
        )
        records = self.session.scalars(
            select(UserRecord)
            .where(condition)
            .order_by(UserRecord.created_at.desc(), UserRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page([_user(record) for record in records], total, limit, offset)

    def set_password(self, user_id: UUID, password_hash: str) -> None:
        """Store only the adaptive hash."""
        self.session.execute(
            update(UserRecord).where(UserRecord.id == user_id).values(password_hash=password_hash)
        )

    def set_active(self, user_id: UUID, is_active: bool) -> None:
        """Change active state only after the service checks role and scope."""
        self.session.execute(
            update(UserRecord).where(UserRecord.id == user_id).values(is_active=is_active)
        )

    def add_session(self, session: Session) -> None:
        """Insert no plaintext authentication token."""
        self.session.add(SessionRecord(**asdict(session)))
        self.session.flush()

    def find_session(self, token_digest: str) -> Session | None:
        """Read session facts using a constant-size digest lookup."""
        record = self.session.scalar(
            select(SessionRecord).where(SessionRecord.token_digest == token_digest)
        )
        return (
            Session(
                record.id,
                record.user_id,
                record.token_digest,
                record.csrf_token,
                _utc(record.created_at),
                _utc(record.expires_at),
            )
            if record
            else None
        )

    def remove_session(self, session_id: UUID) -> None:
        """Revoke one session."""
        self.session.execute(delete(SessionRecord).where(SessionRecord.id == session_id))

    def revoke_sessions(self, user_id: UUID) -> None:
        """Revoke every device session of a deactivated/password-changed account."""
        self.session.execute(delete(SessionRecord).where(SessionRecord.user_id == user_id))

    def remove_expired_sessions(self, now: datetime) -> None:
        """Remove expired sessions during login; no background scheduler is required."""
        self.session.execute(delete(SessionRecord).where(SessionRecord.expires_at <= now))

    def lock_login_limit(self, source_key: str, now: datetime) -> tuple[int, datetime]:
        """Create-if-absent atomically, then lock the direct-source failure window."""
        insert = (
            pg_insert if self.session.get_bind().dialect.name == "postgresql" else sqlite_insert
        )
        statement = (
            insert(LoginLimitRecord)
            .values(id=uuid4(), source_key=source_key, failures=0, window_start=now)
            .on_conflict_do_nothing(index_elements=["source_key"])
        )
        self.session.execute(statement)
        record = self.session.scalar(
            select(LoginLimitRecord)
            .where(LoginLimitRecord.source_key == source_key)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert record is not None
        return record.failures, _utc(record.window_start)

    def set_login_failures(self, source_key: str, failures: int, window_start: datetime) -> None:
        """Persist failed outcomes even when the eventual HTTP status is 401."""
        self.session.execute(
            update(LoginLimitRecord)
            .where(LoginLimitRecord.source_key == source_key)
            .values(failures=failures, window_start=window_start)
        )

    def add_audit(self, event: AuditEvent) -> None:
        """Append minimal audit metadata."""
        values = asdict(event)
        values.pop("actor_display_name")
        self.session.add(AuditRecord(**values))
        self.session.flush()

    def list_audits(self, organization_id: UUID, limit: int, offset: int) -> Page[AuditEvent]:
        """Never return events from other organizations."""
        condition = AuditRecord.organization_id == organization_id
        total = (
            self.session.scalar(select(func.count()).select_from(AuditRecord).where(condition)) or 0
        )
        records = self.session.execute(
            select(AuditRecord, UserRecord.display_name)
            .outerjoin(
                UserRecord,
                (UserRecord.id == AuditRecord.actor_user_id)
                & (UserRecord.organization_id == AuditRecord.organization_id),
            )
            .where(condition)
            .order_by(AuditRecord.created_at.desc(), AuditRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page(
            [
                AuditEvent(
                    record.id,
                    record.organization_id,
                    record.actor_user_id,
                    record.action,
                    record.entity_type,
                    record.entity_id,
                    _utc(record.created_at),
                    name,
                )
                for record, name in records
            ],
            total,
            limit,
            offset,
        )

    def count_legacy_plots(self) -> int:
        """Count preserved M1 plots with no assigned organization."""
        return (
            self.session.scalar(
                select(func.count())
                .select_from(PlotRecord)
                .where(PlotRecord.organization_id.is_(None))
            )
            or 0
        )

    def adopt_legacy_plots(self, organization_id: UUID) -> int:
        """Assign only currently unowned plots; never transfer another team's plots."""
        ids = list(
            self.session.scalars(
                update(PlotRecord)
                .where(PlotRecord.organization_id.is_(None))
                .values(organization_id=organization_id)
                .returning(PlotRecord.id)
            )
        )
        return len(ids)
