"""Shared transaction, session and CSRF checks before authenticated business operations."""

import secrets
from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Header, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session, sessionmaker

from crop_twin.application.identity_service import IdentityService
from crop_twin.core.settings import Settings
from crop_twin.domain.identity.models import Principal
from crop_twin.domain.identity.rules import Forbidden
from crop_twin.infrastructure.database.identity_repository import SqlIdentityRepository
from crop_twin.infrastructure.database.session import reserve_sqlite_writer as reserve_sqlite_writer
from crop_twin.infrastructure.passwords import Argon2Passwords

SESSION_COOKIE = "crop_twin_session"
session_cookie = APIKeyCookie(name=SESSION_COOKIE, auto_error=False)


def session_factory(request: Request) -> sessionmaker[Session]:
    """Return the lifespan-owned factory without opening a second business transaction."""
    return cast(sessionmaker[Session], request.app.state.session_factory)


def database_session(request: Request) -> Iterator[Session]:
    """Commit before responding; rollback unsuccessful business operations."""
    with session_factory(request).begin() as session:
        if request.method == "POST":
            reserve_sqlite_writer(session)
        yield session


DatabaseDependency = Annotated[Session, Depends(database_session, scope="function")]


def identity_service(request: Request, session: Session) -> IdentityService:
    """Construct a transaction-scoped identity service around the shared hasher."""
    passwords = cast(Argon2Passwords, request.app.state.passwords)
    return IdentityService(SqlIdentityRepository(session), passwords)


def check_origin(request: Request) -> None:
    """Reject foreign/null browser origins; never trust arbitrary forwarding headers."""
    origin = request.headers.get("origin")
    settings = cast(Settings, request.app.state.settings)
    if origin is not None and origin not in settings.allowed_origins:
        raise Forbidden("ORIGIN_REJECTED", "请求来源不允许，请从系统页面操作")


def current_principal(
    request: Request,
    session: DatabaseDependency,
    token: Annotated[str | None, Security(session_cookie)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Principal:
    """Validate current account state and session-bound CSRF for every protected POST."""
    principal = identity_service(request, session).authenticate(
        token, lock=request.method == "POST"
    )
    if request.method == "POST":
        check_origin(request)
        if not csrf_token or not secrets.compare_digest(
            principal.session.csrf_token.encode("utf-8"), csrf_token.encode("utf-8")
        ):
            raise Forbidden("CSRF_REJECTED", "操作验证已失效，请刷新页面后重试")
    return principal


PrincipalDependency = Annotated[Principal, Depends(current_principal, scope="function")]
