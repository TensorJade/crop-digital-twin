"""Immutable farm records and typed inputs; quantities retain their original units."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from crop_twin.domain.pagination import Page as Page

EstablishmentMethod = Literal["direct_sowing", "transplanting"]
EventType = Literal[
    "sowing", "transplanting", "irrigation", "fertilization", "inspection", "harvest"
]
InputUnit = Literal["mm", "m3", "kg/mu", "kg/ha"]


@dataclass(frozen=True)
class PlotInput:
    """Human-reported plot area (mu) and WGS84 point, not a measured polygon."""

    name: str
    area_mu: Decimal
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Plot:
    """Persisted plot facts, with hectares derived from the original area."""

    id: UUID
    name: str
    area_mu: Decimal
    latitude: float
    longitude: float
    created_at: datetime
    organization_id: UUID

    @property
    def area_ha(self) -> Decimal:
        """Convert reported mu to hectares without storing a second area fact."""
        return self.area_mu / Decimal(15)


@dataclass(frozen=True)
class SeasonInput:
    """Rice establishment and optional historical end date."""

    plot_id: UUID
    start_date: date
    establishment_method: EstablishmentMethod
    variety_name: str | None = None
    end_date: date | None = None


@dataclass(frozen=True)
class Season:
    """One rice season, whose inclusive dates must not overlap another season."""

    id: UUID
    plot_id: UUID
    start_date: date
    establishment_method: EstablishmentMethod
    variety_name: str | None
    end_date: date | None
    created_at: datetime
    crop_code: Literal["rice"] = "rice"


@dataclass(frozen=True)
class EventInput:
    """Recorded operation, retaining the operator's submitted quantity and unit."""

    event_type: EventType
    occurred_on: date
    quantity: Decimal | None = None
    unit: InputUnit | None = None
    material_name: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class ManagementEvent:
    """Append-only operation revision; current status is derived when read."""

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
    revision: int = 1
    replaces_event_id: UUID | None = None
    correction_reason: str | None = None
    is_current: bool = True
