"""Concrete SQL implementation of the cohesive farm repository boundary."""

from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from crop_twin.domain.farm.models import (
    EstablishmentMethod,
    EventType,
    InputUnit,
    ManagementEvent,
    Page,
    Plot,
    Season,
)
from crop_twin.infrastructure.database.identity_models import AuditRecord
from crop_twin.infrastructure.database.models import EventRecord, PlotRecord, SeasonRecord


def _utc(value: datetime) -> datetime:
    # SQLite drops timezone metadata; all timestamps are written in UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _plot(record: PlotRecord) -> Plot:
    assert record.organization_id is not None
    return Plot(
        record.id,
        record.name,
        record.area_mu,
        record.latitude,
        record.longitude,
        _utc(record.created_at),
        record.organization_id,
    )


def _season(record: SeasonRecord) -> Season:
    return Season(
        record.id,
        record.plot_id,
        record.start_date,
        cast(EstablishmentMethod, record.establishment_method),
        record.variety_name,
        record.end_date,
        _utc(record.created_at),
    )


def _event(record: EventRecord, is_current: bool) -> ManagementEvent:
    return ManagementEvent(
        id=record.id,
        season_id=record.season_id,
        event_type=cast(EventType, record.event_type),
        occurred_on=record.occurred_on,
        quantity=record.quantity,
        unit=cast(InputUnit | None, record.unit),
        normalized_quantity=record.normalized_quantity,
        normalized_unit=cast(Literal["mm", "kg/ha"] | None, record.normalized_unit),
        material_name=record.material_name,
        notes=record.notes,
        created_at=_utc(record.created_at),
        revision=record.revision,
        replaces_event_id=record.replaces_event_id,
        correction_reason=record.correction_reason,
        is_current=is_current,
    )


class SqlFarmRepository:
    """Translate records and execute bounded SQL within the caller's transaction."""

    def __init__(self, session: Session, organization_id: UUID, actor_id: UUID) -> None:
        self.session = session
        self.organization_id, self.actor_id = organization_id, actor_id

    def _plot_ids(self) -> Select[UUID]:
        return select(PlotRecord.id).where(PlotRecord.organization_id == self.organization_id)

    def _season_ids(self) -> Select[UUID]:
        return select(SeasonRecord.id).where(SeasonRecord.plot_id.in_(self._plot_ids()))

    def record_audit(self, action: str, entity_type: str, entity_id: UUID) -> None:
        """Append the mutation audit in the same transaction as the farm fact."""
        self.session.add(
            AuditRecord(
                id=uuid4(),
                organization_id=self.organization_id,
                actor_user_id=self.actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                created_at=datetime.now(UTC),
            )
        )
        self.session.flush()

    def get_plot(self, plot_id: UUID, *, lock: bool = False) -> Plot | None:
        """Read the parent plot, optionally serializing writes to its seasons."""
        statement = select(PlotRecord).where(
            PlotRecord.id == plot_id, PlotRecord.organization_id == self.organization_id
        )
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        record = self.session.scalar(statement)
        return _plot(record) if record is not None else None

    def add_plot(self, plot: Plot) -> None:
        """Flush a new manual plot before the HTTP response is returned."""
        self.session.add(PlotRecord(**asdict(plot)))
        self.session.flush()

    def list_plots(self, limit: int, offset: int) -> Page[Plot]:
        """Read plot pagination in deterministic newest-first order."""
        condition = PlotRecord.organization_id == self.organization_id
        total = (
            self.session.scalar(select(func.count()).select_from(PlotRecord).where(condition)) or 0
        )
        records = self.session.scalars(
            select(PlotRecord)
            .where(condition)
            .order_by(PlotRecord.created_at.desc(), PlotRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page([_plot(record) for record in records], total, limit, offset)

    def get_season(self, season_id: UUID, *, lock: bool = False) -> Season | None:
        """Read a season, optionally serializing operations and its closing date."""
        statement = select(SeasonRecord).where(
            SeasonRecord.id == season_id, SeasonRecord.plot_id.in_(self._plot_ids())
        )
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        record = self.session.scalar(statement)
        return _season(record) if record is not None else None

    def add_season(self, season: Season) -> None:
        """Insert a rice season; crop code is fixed by this module's scope."""
        values = asdict(season)
        values.pop("crop_code")
        self.session.add(SeasonRecord(**values))
        self.session.flush()

    def close_season(self, season_id: UUID, end_date: date) -> None:
        """Update only the checked closing date of an existing season."""
        record = self.session.get(SeasonRecord, season_id)
        if record is None:
            raise RuntimeError("Season disappeared inside a locked transaction")
        record.end_date = end_date
        self.session.flush()

    def seasons_for_plot(self, plot_id: UUID) -> list[Season]:
        """Read a plot's short season history for interval validation."""
        return [
            _season(record)
            for record in self.session.scalars(
                select(SeasonRecord).where(
                    SeasonRecord.plot_id == plot_id, SeasonRecord.plot_id.in_(self._plot_ids())
                )
            )
        ]

    def list_seasons(self, plot_id: UUID, limit: int, offset: int) -> Page[Season]:
        """Return season pagination for one checked plot."""
        condition = (SeasonRecord.plot_id == plot_id) & SeasonRecord.plot_id.in_(self._plot_ids())
        total = (
            self.session.scalar(select(func.count()).select_from(SeasonRecord).where(condition))
            or 0
        )
        records = self.session.scalars(
            select(SeasonRecord)
            .where(condition)
            .order_by(SeasonRecord.start_date.desc(), SeasonRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page([_season(record) for record in records], total, limit, offset)

    def get_event(self, event_id: UUID) -> ManagementEvent | None:
        """Read an event with current status derived from retained successors."""
        successor = aliased(EventRecord)
        current = (
            ~select(successor.id).where(successor.replaces_event_id == EventRecord.id).exists()
        )
        row = self.session.execute(
            select(EventRecord, current).where(
                EventRecord.id == event_id, EventRecord.season_id.in_(self._season_ids())
            )
        ).first()
        return _event(row[0], row[1]) if row is not None else None

    def add_event(self, event: ManagementEvent) -> None:
        """Insert a revision without modifying the previous operation."""
        values = asdict(event)
        values.pop("is_current")
        self.session.add(EventRecord(**values))
        self.session.flush()

    def has_current_event_after(self, season_id: UUID, end_date: date) -> bool:
        """Reject a closing date before a still-current operation."""
        successor = aliased(EventRecord)
        current = (
            ~select(successor.id).where(successor.replaces_event_id == EventRecord.id).exists()
        )
        return bool(
            self.session.scalar(
                select(EventRecord.id)
                .where(
                    EventRecord.season_id == season_id,
                    EventRecord.occurred_on > end_date,
                    current,
                    EventRecord.season_id.in_(self._season_ids()),
                )
                .limit(1)
            )
        )

    def list_events(
        self, season_id: UUID, limit: int, offset: int, *, include_history: bool = False
    ) -> Page[ManagementEvent]:
        """Page current/all revisions with one correlated successor predicate."""
        successor = aliased(EventRecord)
        current = (
            ~select(successor.id).where(successor.replaces_event_id == EventRecord.id).exists()
        )
        condition = (EventRecord.season_id == season_id) & EventRecord.season_id.in_(
            self._season_ids()
        )
        filters = [condition] if include_history else [condition, current]
        total = (
            self.session.scalar(select(func.count()).select_from(EventRecord).where(*filters)) or 0
        )
        rows = self.session.execute(
            select(EventRecord, current)
            .where(*filters)
            .order_by(
                EventRecord.occurred_on.desc(), EventRecord.created_at.desc(), EventRecord.id.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        return Page([_event(row[0], row[1]) for row in rows], total, limit, offset)
