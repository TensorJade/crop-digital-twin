"""Identity validation, authorization and safe errors."""

import re

from crop_twin.domain.identity.models import User


class IdentityError(Exception):
    """Safe identity error with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code, self.message = code, message


class Unauthorized(IdentityError):
    """No usable authentication or credentials."""


class Forbidden(IdentityError):
    """The authenticated operation is outside the granted scope."""


class IdentityConflict(IdentityError):
    """The requested account fact conflicts with existing facts."""


class IdentityNotFound(IdentityError):
    """No account resource exists inside this organization scope."""


class LoginLimited(IdentityError):
    """The persisted source failure window is exhausted."""


def canonical_username(username: str) -> str:
    """Use one lowercase ASCII login spelling for creation and lookup."""
    return username.strip().lower()


def validate_account(username: str, display_name: str, password: str) -> str:
    """Validate creation without stripping or changing the password."""
    normalized = canonical_username(username)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", normalized):
        raise IdentityError("INVALID_USERNAME", "账号用 3–64 位字母、数字、下划线或短横线")
    if not 1 <= len(display_name.strip()) <= 80:
        raise IdentityError("INVALID_DISPLAY_NAME", "请填写 1–80 字的姓名或称呼")
    validate_password(password)
    return normalized


def validate_password(password: str) -> None:
    """Permit long passphrases without arbitrary character-class requirements."""
    if not 12 <= len(password) <= 128:
        raise IdentityError("INVALID_PASSWORD", "密码应为 12–128 个字符")


def require_owner(user: User) -> None:
    """Restrict team account and audit administration."""
    if user.role != "owner":
        raise Forbidden("OWNER_REQUIRED", "此操作需要本组织管理员权限")


def require_writer(user: User) -> None:
    """Readers cannot create or modify farm facts."""
    if user.role == "viewer":
        raise Forbidden("READ_ONLY", "当前账号仅可查看，不能修改农田记录")
