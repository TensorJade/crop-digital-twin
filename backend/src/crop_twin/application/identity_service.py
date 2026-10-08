"""Account and session use cases; authentication failures are committed results."""

import hashlib
import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from crop_twin.application.identity_repository import IdentityRepository, PasswordHasher
from crop_twin.domain.identity.models import (
    AuditEvent,
    LoginResult,
    Organization,
    Principal,
    Role,
    Session,
    User,
)
from crop_twin.domain.identity.rules import (
    Forbidden,
    IdentityConflict,
    IdentityError,
    IdentityNotFound,
    Unauthorized,
    canonical_username,
    require_owner,
    validate_account,
    validate_password,
)
from crop_twin.domain.pagination import Page

SESSION_LIFETIME = timedelta(hours=8)
LOGIN_WINDOW = timedelta(minutes=15)
MAX_LOGIN_FAILURES = 5


def token_digest(token: str) -> str:
    """Digest a cryptographically random token, not a low-entropy password."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class IdentityService:
    """Identity rules depend on storage and password capabilities, not HTTP or SQL."""

    def __init__(self, repository: IdentityRepository, passwords: PasswordHasher) -> None:
        self.repository, self.passwords = repository, passwords

    def bootstrap(
        self,
        username: str,
        display_name: str,
        password: str,
        organization_name: str,
        *,
        adopt_legacy: bool = False,
    ) -> tuple[User, int]:
        """Create an initial owner; legacy data ownership requires an explicit decision."""
        normalized = validate_account(username, display_name, password)
        if not 1 <= len(organization_name.strip()) <= 100:
            raise IdentityError("INVALID_ORGANIZATION", "组织名称应为 1–100 字")
        if self.repository.find_user(normalized):
            raise IdentityConflict("USERNAME_UNAVAILABLE", "该账号名称不可用")
        if self.repository.count_legacy_plots() and not adopt_legacy:
            raise IdentityConflict(
                "LEGACY_OWNERSHIP_REQUIRED", "存在旧地块，请明确是否使用 --adopt-legacy 接收"
            )
        now = datetime.now(UTC)
        organization = Organization(uuid4(), organization_name.strip(), now)
        self.repository.add_organization(organization)
        user = User(
            uuid4(),
            organization.id,
            normalized,
            display_name.strip(),
            "owner",
            True,
            now,
            self.passwords.hash(password),
        )
        self.repository.add_user(user)
        adopted = self.repository.adopt_legacy_plots(organization.id) if adopt_legacy else 0
        self._audit(user, "identity.bootstrap", "organization", organization.id)
        if adopted:
            self._audit(user, "identity.legacy_adopted", "organization", organization.id)
        return user, adopted

    def login(self, username: str, password: str, source: str) -> LoginResult:
        """Persist failures before the HTTP layer returns 401/429; do not raise on mismatch."""
        now = datetime.now(UTC)
        source_key = token_digest(source)
        failures, start = self.repository.lock_login_limit(source_key, now)
        if now - start >= LOGIN_WINDOW:
            failures, start = 0, now
        if failures >= MAX_LOGIN_FAILURES:
            return LoginResult(is_limited=True)
        user = self.repository.find_user(canonical_username(username), lock=True)
        valid = self.passwords.verify(user.password_hash if user else None, password)
        if user is None or not user.is_active or not valid:
            self.repository.set_login_failures(source_key, failures + 1, start)
            return LoginResult()
        self.repository.set_login_failures(source_key, 0, now)
        if self.passwords.needs_rehash(user.password_hash):
            self.repository.set_password(user.id, self.passwords.hash(password))
        self.repository.remove_expired_sessions(now)
        token = secrets.token_urlsafe(32)
        session = Session(
            uuid4(),
            user.id,
            token_digest(token),
            secrets.token_urlsafe(32),
            now,
            now + SESSION_LIFETIME,
        )
        self.repository.add_session(session)
        self._audit(user, "auth.login", "user", user.id)
        return LoginResult(Principal(user, session), token)

    def authenticate(self, token: str | None, *, lock: bool = False) -> Principal:
        """Resolve an unexpired session and the account's current active state."""
        session = self.repository.find_session(token_digest(token)) if token else None
        if session is None or session.expires_at <= datetime.now(UTC):
            raise Unauthorized("LOGIN_REQUIRED", "登录已失效，请重新登录")
        user = self.repository.get_user(session.user_id, lock=lock)
        if user is None or not user.is_active:
            raise Unauthorized("LOGIN_REQUIRED", "登录已失效，请重新登录")
        # A concurrent password change may revoke the session while the user lock is acquired.
        if lock and self.repository.find_session(session.token_digest) is None:
            raise Unauthorized("LOGIN_REQUIRED", "登录已失效，请重新登录")
        return Principal(user, session)

    def organization(self, user: User) -> Organization:
        """Read only the account's organization, never a client-selected organization."""
        organization = self.repository.get_organization(user.organization_id)
        if organization is None:
            raise Unauthorized("LOGIN_REQUIRED", "账号归属不可用，请联系管理员")
        return organization

    def logout(self, principal: Principal) -> None:
        """Revoke the current session in the same transaction as its audit."""
        self.repository.remove_session(principal.session.id)
        self._audit(principal.user, "auth.logout", "user", principal.user.id)

    def change_password(self, principal: Principal, current: str, new: str) -> None:
        """Require current credentials and revoke all sessions after changing the hash."""
        validate_password(new)
        if not self.passwords.verify(principal.user.password_hash, current):
            raise IdentityError("INVALID_CREDENTIALS", "账号或密码错误")
        self.repository.set_password(principal.user.id, self.passwords.hash(new))
        self.repository.revoke_sessions(principal.user.id)
        self._audit(principal.user, "auth.password_changed", "user", principal.user.id)

    def create_user(
        self, actor: User, username: str, display_name: str, password: str, role: Role
    ) -> User:
        """An owner creates operators/readers only inside their own organization."""
        require_owner(actor)
        if role not in ("operator", "viewer"):
            raise Forbidden("INVALID_MEMBER_ROLE", "成员角色请选择农田管理或仅查看")
        normalized = validate_account(username, display_name, password)
        if self.repository.find_user(normalized):
            raise IdentityConflict("USERNAME_UNAVAILABLE", "该账号名称不可用")
        user = User(
            uuid4(),
            actor.organization_id,
            normalized,
            display_name.strip(),
            role,
            True,
            datetime.now(UTC),
            self.passwords.hash(password),
        )
        self.repository.add_user(user)
        self._audit(actor, "identity.user_created", "user", user.id)
        return user

    def set_user_active(self, actor: User, user_id: UUID, is_active: bool) -> User:
        """Keep owners usable and revoke every session when a member is disabled."""
        require_owner(actor)
        user = self.repository.get_user(user_id, lock=True)
        if user is None or user.organization_id != actor.organization_id:
            raise IdentityNotFound("USER_NOT_FOUND", "找不到该成员")
        if user.role == "owner":
            raise Forbidden("OWNER_PROTECTED", "不能停用管理员账号")
        if user.is_active != is_active:
            self.repository.set_active(user.id, is_active)
            if not is_active:
                self.repository.revoke_sessions(user.id)
            self._audit(
                actor,
                "identity.user_activated" if is_active else "identity.user_deactivated",
                "user",
                user.id,
            )
        return replace(user, is_active=is_active)

    def list_users(self, actor: User, limit: int, offset: int) -> Page[User]:
        """Return only this owner's team."""
        require_owner(actor)
        return self.repository.list_users(actor.organization_id, limit, offset)

    def list_audits(self, actor: User, limit: int, offset: int) -> Page[AuditEvent]:
        """Only an owner sees organization-scoped audit metadata."""
        require_owner(actor)
        return self.repository.list_audits(actor.organization_id, limit, offset)

    def _audit(self, actor: User, action: str, entity_type: str, entity_id: UUID) -> None:
        self.repository.add_audit(
            AuditEvent(
                uuid4(),
                actor.organization_id,
                actor.id,
                action,
                entity_type,
                entity_id,
                datetime.now(UTC),
            )
        )
