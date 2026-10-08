"""Scoped SQL persistence for typed input assets and immutable season snapshots."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crop_twin.domain.pagination import Page
from crop_twin.domain.simulation.models import AssetKind, InputAsset, SimulationInput
from crop_twin.infrastructure.database.input_models import InputAssetRecord, SimulationInputRecord


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _asset(record: InputAssetRecord) -> InputAsset:
    return InputAsset(
        record.id,
        record.organization_id,
        record.plot_id,
        cast(AssetKind, record.kind),
        record.name,
        record.source,
        record.source_license,
        record.payload,
        record.content_hash,
        record.actor_user_id,
        _utc(record.created_at),
    )


def _snapshot(record: SimulationInputRecord) -> SimulationInput:
    return SimulationInput(
        record.id,
        record.organization_id,
        record.season_id,
        record.version,
        record.payload,
        record.content_hash,
        record.actor_user_id,
        _utc(record.created_at),
    )


class SqlInputRepository:
    """Every query filters the caller's organization, including foreign IDs."""

    def __init__(self, session: Session, organization_id: UUID) -> None:
        self.session, self.organization_id = session, organization_id

    def add_asset(self, asset: InputAsset) -> None:
        """Persist a validated immutable asset in the caller's transaction."""
        self.session.add(InputAssetRecord(**asdict(asset)))
        self.session.flush()

    def get_asset(self, asset_id: UUID) -> InputAsset | None:
        """Hide foreign assets as nonexistent."""
        record = self.session.scalar(
            select(InputAssetRecord).where(
                InputAssetRecord.id == asset_id,
                InputAssetRecord.organization_id == self.organization_id,
            )
        )
        return _asset(record) if record else None

    def list_assets(
        self, kind: AssetKind, plot_id: UUID | None, limit: int, offset: int
    ) -> Page[InputAsset]:
        """Page one input type for a checked plot, or the team's crop library."""
        conditions = (
            InputAssetRecord.organization_id == self.organization_id,
            InputAssetRecord.kind == kind,
            InputAssetRecord.plot_id == plot_id,
        )
        total = (
            self.session.scalar(
                select(func.count()).select_from(InputAssetRecord).where(*conditions)
            )
            or 0
        )
        records = self.session.scalars(
            select(InputAssetRecord)
            .where(*conditions)
            .order_by(InputAssetRecord.created_at.desc(), InputAssetRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page([_asset(record) for record in records], total, limit, offset)

    def next_version(self, season_id: UUID) -> int:
        """The service holds the season row lock across allocation and insert."""
        highest = (
            self.session.scalar(
                select(func.max(SimulationInputRecord.version)).where(
                    SimulationInputRecord.organization_id == self.organization_id,
                    SimulationInputRecord.season_id == season_id,
                )
            )
            or 0
        )
        return highest + 1

    def add_snapshot(self, snapshot: SimulationInput) -> None:
        """Store the exact frozen payload with its digest."""
        self.session.add(SimulationInputRecord(**asdict(snapshot)))
        self.session.flush()

    def get_snapshot(self, input_id: UUID) -> SimulationInput | None:
        """Read only the team's snapshot."""
        record = self.session.scalar(
            select(SimulationInputRecord).where(
                SimulationInputRecord.id == input_id,
                SimulationInputRecord.organization_id == self.organization_id,
            )
        )
        return _snapshot(record) if record else None

    def list_snapshots(self, season_id: UUID, limit: int, offset: int) -> Page[SimulationInput]:
        """Page version summaries without allowing cross-organization season access."""
        conditions = (
            SimulationInputRecord.organization_id == self.organization_id,
            SimulationInputRecord.season_id == season_id,
        )
        total = (
            self.session.scalar(
                select(func.count()).select_from(SimulationInputRecord).where(*conditions)
            )
            or 0
        )
        records = self.session.scalars(
            select(SimulationInputRecord)
            .where(*conditions)
            .order_by(SimulationInputRecord.version.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page([_snapshot(record) for record in records], total, limit, offset)
