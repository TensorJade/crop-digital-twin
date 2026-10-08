"""Identity HTTP schemas expose only public user/organization facts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from crop_twin.api.v1.schemas import OutputModel
from crop_twin.domain.identity.models import Role


class IdentityInput(BaseModel):
    """Passwords are secret types and are never stripped by general string normalization."""

    model_config = ConfigDict(extra="forbid")


class LoginInput(IdentityInput):
    """Bounded credentials; username canonicalization belongs to the service."""

    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)


class UserCreate(IdentityInput):
    """No organization ID or owner role can be supplied by a member-creation client."""

    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=80)
    password: SecretStr = Field(min_length=12, max_length=128)
    role: Literal["operator", "viewer"]


class UserActive(IdentityInput):
    """An explicit boolean; string/integer truthiness is not accepted."""

    is_active: bool = Field(strict=True)


class PasswordChange(IdentityInput):
    """Require old credentials; successful change revokes every session."""

    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=12, max_length=128)


class UserResponse(OutputModel):
    """Password/hash/session credentials are deliberately absent."""

    id: UUID
    organization_id: UUID
    username: str
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime


class OrganizationResponse(OutputModel):
    """The currently authenticated farm team."""

    id: UUID
    name: str
    created_at: datetime


class IdentityResponse(OutputModel):
    """Session-bound CSRF can be recovered after reload; the auth token stays HttpOnly."""

    user: UserResponse
    organization: OrganizationResponse
    csrf_token: str
    expires_at: datetime


class MessageResponse(OutputModel):
    """A successful operation with no secret body."""

    message: str


class AuditResponse(OutputModel):
    """Append-only metadata scoped to the current organization."""

    id: UUID
    organization_id: UUID
    actor_user_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    created_at: datetime
    actor_display_name: str | None
