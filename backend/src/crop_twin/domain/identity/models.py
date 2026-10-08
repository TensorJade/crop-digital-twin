"""Identity facts without HTTP, database or password-library dependencies."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

Role = Literal["owner", "operator", "viewer"]


@dataclass(frozen=True)
class Organization:
    """One farm team; its members share its plots."""

    id: UUID
    name: str
    created_at: datetime


@dataclass(frozen=True)
class User:
    """An account belongs to one team; hashes are never part of public responses."""

    id: UUID
    organization_id: UUID
    username: str
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime
    password_hash: str = field(repr=False)


@dataclass(frozen=True)
class Session:
    """The database has a token digest, never the authentication token itself."""

    id: UUID
    user_id: UUID
    token_digest: str = field(repr=False)
    csrf_token: str = field(repr=False)
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class Principal:
    """The account and session checked inside the current request transaction."""

    user: User
    session: Session


@dataclass(frozen=True)
class LoginResult:
    """A committed failed attempt, rate limit, or newly established session."""

    principal: Principal | None = None
    token: str | None = field(default=None, repr=False)
    is_limited: bool = False


@dataclass(frozen=True)
class AuditEvent:
    """Append-only operation metadata, excluding credentials and request bodies."""

    id: UUID
    organization_id: UUID
    actor_user_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    created_at: datetime
    actor_display_name: str | None = None
