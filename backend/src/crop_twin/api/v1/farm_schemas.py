"""M1 HTTP contracts; business rules stay in the farm domain/application."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from crop_twin.domain.farm.models import EstablishmentMethod, EventType, InputUnit

PositiveQuantity = Annotated[Decimal, Field(gt=0, le=1_000_000, decimal_places=6)]


class InputModel(BaseModel):
    """Reject unknown input fields and non-finite numeric values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class PlotCreate(InputModel):
    """Reported area in mu and a WGS84 point."""

    name: str = Field(min_length=1, max_length=80)
    area_mu: PositiveQuantity
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SeasonCreate(InputModel):
    """Rice establishment; absent variety is recorded as unknown."""

    plot_id: UUID
    start_date: date
    establishment_method: EstablishmentMethod
    variety_name: str | None = Field(default=None, max_length=100)
    end_date: date | None = None


class SeasonClose(InputModel):
    """Confirmed season end date, not a predicted harvest date."""

    end_date: date


class EventFields(InputModel):
    """Original operation quantity and notes; normalization is a domain concern."""

    event_type: EventType
    occurred_on: date
    quantity: PositiveQuantity | None = None
    unit: InputUnit | None = None
    material_name: str | None = Field(default=None, max_length=100)
    notes: str = Field(default="", max_length=2000)


class EventCreate(EventFields):
    """New operation in a specified season."""

    season_id: UUID


class EventCorrection(EventFields):
    """A full replacement operation with a required explanation."""

    correction_reason: str = Field(min_length=1, max_length=240)


class OutputModel(BaseModel):
    """Serialize immutable application records, including exact decimal strings."""

    model_config = ConfigDict(from_attributes=True)


class PlotResponse(OutputModel):
    """Reported plot facts and derived hectares."""

    id: UUID
    name: str
    area_mu: Decimal
    area_ha: Decimal
    latitude: float
    longitude: float
    created_at: datetime


class SeasonResponse(OutputModel):
    """The rice season state and establishment facts."""

    id: UUID
    plot_id: UUID
    crop_code: Literal["rice"]
    start_date: date
    end_date: date | None
    establishment_method: EstablishmentMethod
    variety_name: str | None
    created_at: datetime


class EventResponse(OutputModel):
    """Original/standard quantities and a traceable operation revision."""

    id: UUID
    season_id: UUID
    event_type: EventType
    occurred_on: date
    quantity: Decimal | None
    unit: InputUnit | None
    normalized_quantity: Decimal | None
    normalized_unit: Literal["mm", "kg/ha"] | None
    material_name: str | None
    notes: str
    created_at: datetime
    revision: int
    replaces_event_id: UUID | None
    correction_reason: str | None
    is_current: bool


class PageResponse[T](OutputModel):
    """Bounded collection response with total count and navigation information."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    """Safe business/storage error, without SQL or credential exposure."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Shared documented error response for M1 routes."""

    detail: ErrorDetail
