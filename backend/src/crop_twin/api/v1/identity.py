"""Account HTTP adapters; failed login counting commits before returning an error."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from crop_twin.api.v1.dependencies import (
    SESSION_COOKIE,
    DatabaseDependency,
    PrincipalDependency,
    check_origin,
    identity_service,
    reserve_sqlite_writer,
    session_factory,
)
from crop_twin.api.v1.identity_schemas import (
    AuditResponse,
    IdentityResponse,
    LoginInput,
    MessageResponse,
    OrganizationResponse,
    PasswordChange,
    UserActive,
    UserCreate,
    UserResponse,
)
from crop_twin.api.v1.schemas import ErrorResponse, PageResponse
from crop_twin.application.identity_service import SESSION_LIFETIME
from crop_twin.core.settings import Settings
from crop_twin.domain.identity.rules import LoginLimited, Unauthorized

router = APIRouter(
    prefix="/api/v1",
    tags=["identity"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 429, 503)},
)
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/auth/login", response_model=IdentityResponse, operation_id="login")
def login(data: LoginInput, request: Request, response: Response) -> IdentityResponse:
    """Issue a revocable Cookie; never put a session authentication token in JSON."""
    check_origin(request)
    with session_factory(request).begin() as session:
        reserve_sqlite_writer(session)
        service = identity_service(request, session)
        source = request.client.host if request.client else "unknown"
        result = service.login(data.username, data.password.get_secret_value(), source)
        body = None
        if result.principal:
            body = IdentityResponse(
                user=UserResponse.model_validate(result.principal.user),
                organization=OrganizationResponse.model_validate(
                    service.organization(result.principal.user)
                ),
                csrf_token=result.principal.session.csrf_token,
                expires_at=result.principal.session.expires_at,
            )
    # These errors are raised after the failed-attempt transaction has committed.
    if result.is_limited:
        raise LoginLimited("LOGIN_LIMITED", "尝试过于频繁，请 15 分钟后重试")
    if body is None or result.token is None:
        raise Unauthorized("INVALID_CREDENTIALS", "账号或密码错误")
    settings = cast(Settings, request.app.state.settings)
    response.set_cookie(
        SESSION_COOKIE,
        result.token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api",
        max_age=int(SESSION_LIFETIME.total_seconds()),
    )
    return body


@router.get("/auth/me", response_model=IdentityResponse, operation_id="getCurrentIdentity")
def get_current_identity(
    request: Request, session: DatabaseDependency, principal: PrincipalDependency
) -> IdentityResponse:
    """Recover the current user and CSRF after reload without localStorage credentials."""
    return IdentityResponse(
        user=UserResponse.model_validate(principal.user),
        organization=OrganizationResponse.model_validate(
            identity_service(request, session).organization(principal.user)
        ),
        csrf_token=principal.session.csrf_token,
        expires_at=principal.session.expires_at,
    )


@router.post("/auth/logout", response_model=MessageResponse, operation_id="logout")
def logout(
    request: Request,
    response: Response,
    session: DatabaseDependency,
    principal: PrincipalDependency,
) -> object:
    """Revoke this session server-side and clear the matching Cookie path."""
    identity_service(request, session).logout(principal)
    settings = cast(Settings, request.app.state.settings)
    response.delete_cookie(
        SESSION_COOKIE, path="/api", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )
    return {"message": "已退出登录"}


@router.post("/auth/password", response_model=MessageResponse, operation_id="changePassword")
def change_password(
    data: PasswordChange,
    request: Request,
    response: Response,
    session: DatabaseDependency,
    principal: PrincipalDependency,
) -> object:
    """Changing the password revokes all device sessions, including this one."""
    identity_service(request, session).change_password(
        principal, data.current_password.get_secret_value(), data.new_password.get_secret_value()
    )
    settings = cast(Settings, request.app.state.settings)
    response.delete_cookie(
        SESSION_COOKIE, path="/api", secure=settings.cookie_secure, httponly=True, samesite="lax"
    )
    return {"message": "密码已修改，请重新登录"}


@router.get("/organization", response_model=OrganizationResponse, operation_id="getOrganization")
def get_organization(
    request: Request, session: DatabaseDependency, principal: PrincipalDependency
) -> object:
    """Read only the session's organization."""
    return identity_service(request, session).organization(principal.user)


@router.get("/users", response_model=PageResponse[UserResponse], operation_id="listUsers")
def list_users(
    request: Request,
    session: DatabaseDependency,
    principal: PrincipalDependency,
    limit: Limit = 50,
    offset: Offset = 0,
) -> object:
    """An owner lists members of their organization."""
    return identity_service(request, session).list_users(principal.user, limit, offset)


@router.post("/users", response_model=UserResponse, status_code=201, operation_id="createUser")
def create_user(
    data: UserCreate, request: Request, session: DatabaseDependency, principal: PrincipalDependency
) -> object:
    """An owner creates an operator or reader; ownership is assigned server-side."""
    return identity_service(request, session).create_user(
        principal.user,
        data.username,
        data.display_name,
        data.password.get_secret_value(),
        data.role,
    )


@router.post("/users/{user_id}/active", response_model=UserResponse, operation_id="setUserActive")
def set_user_active(
    user_id: UUID,
    data: UserActive,
    request: Request,
    session: DatabaseDependency,
    principal: PrincipalDependency,
) -> object:
    """Activate/deactivate team members while protecting the administrator."""
    return identity_service(request, session).set_user_active(
        principal.user, user_id, data.is_active
    )


@router.get(
    "/audit-events", response_model=PageResponse[AuditResponse], operation_id="listAuditEvents"
)
def list_audit_events(
    request: Request,
    session: DatabaseDependency,
    principal: PrincipalDependency,
    limit: Limit = 50,
    offset: Offset = 0,
) -> object:
    """Return paginated minimal audit metadata for this owner's organization."""
    return identity_service(request, session).list_audits(principal.user, limit, offset)
