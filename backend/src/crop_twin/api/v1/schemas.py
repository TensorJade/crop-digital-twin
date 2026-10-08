"""Shared transport responses, independent of individual business modules."""

from pydantic import BaseModel, ConfigDict


class OutputModel(BaseModel):
    """Serialize only declared fields from immutable application records."""

    model_config = ConfigDict(from_attributes=True)


class PageResponse[T](OutputModel):
    """A bounded collection response."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    """Safe business/storage error, with no credentials or SQL parameters."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Documented stable error envelope."""

    detail: ErrorDetail
