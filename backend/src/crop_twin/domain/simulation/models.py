"""Input records own their explicit JSON payloads, with no HTTP or ORM dependency."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, cast
from uuid import UUID

from crop_engine.inputs import InputReport

AssetKind = Literal["soil", "crop", "weather"]


@dataclass(frozen=True)
class AssetInput:
    """A validated typed import crosses the application boundary as portable data."""

    kind: AssetKind
    plot_id: UUID | None
    name: str
    source: str
    source_license: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class InputAsset:
    """Append-only input version with declared source and canonical content hash."""

    id: UUID
    organization_id: UUID
    plot_id: UUID | None
    kind: AssetKind
    name: str
    source: str
    source_license: str
    payload: dict[str, Any]
    content_hash: str
    actor_user_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class SnapshotInput:
    """Select exact asset versions and explicit emergence/cutoff dates."""

    season_id: UUID
    soil_asset_id: UUID
    crop_asset_id: UUID
    weather_asset_id: UUID
    emergence_date: date
    cutoff_date: date


@dataclass(frozen=True)
class SimulationInput:
    """An immutable season snapshot; version increments under the season row lock."""

    id: UUID
    organization_id: UUID
    season_id: UUID
    version: int
    payload: dict[str, Any]
    content_hash: str
    actor_user_id: UUID
    created_at: datetime

    @property
    def report(self) -> InputReport:
        """Expose preflight status without listing the complete input payload."""
        return cast(InputReport, self.payload["report"])
