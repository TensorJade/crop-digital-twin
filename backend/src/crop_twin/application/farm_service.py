"""Farm use cases; callers supply one transaction-scoped repository per operation."""

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from crop_twin.application.farm_repository import FarmRepository
from crop_twin.domain.farm.models import (
    EventInput,
    ManagementEvent,
    Page,
    Plot,
    PlotInput,
    Season,
    SeasonInput,
)
from crop_twin.domain.farm.rules import (
    FarmConflict,
    FarmError,
    FarmNotFound,
    normalize_event_quantity,
    seasons_overlap,
    validate_event_date,
    validate_plot,
    validate_season_dates,
)


class FarmService:
    """Coordinate farm rules and persistence without depending on API or SQLAlchemy."""

    def __init__(self, repository: FarmRepository) -> None:
        self.repository = repository

    def get_plot(self, plot_id: UUID, *, lock: bool = False) -> Plot:
        """Read a plot or raise a safe not-found error."""
        plot = self.repository.get_plot(plot_id, lock=lock)
        if plot is None:
            raise FarmNotFound("PLOT_NOT_FOUND", "找不到该地块，请重新选择")
        return plot

    def create_plot(self, data: PlotInput) -> Plot:
        """Persist validated manual plot facts."""
        validate_plot(data)
        plot = Plot(
            uuid4(),
            data.name.strip(),
            data.area_mu,
            data.latitude,
            data.longitude,
            datetime.now(UTC),
        )
        self.repository.add_plot(plot)
        return plot

    def list_plots(self, limit: int, offset: int) -> Page[Plot]:
        """Return a bounded plot list."""
        return self.repository.list_plots(limit, offset)

    def get_season(self, season_id: UUID, *, lock: bool = False) -> Season:
        """Read a season or reject a missing logical reference."""
        season = self.repository.get_season(season_id, lock=lock)
        if season is None:
            raise FarmNotFound("SEASON_NOT_FOUND", "找不到该种植季，请重新选择")
        return season

    def create_season(self, data: SeasonInput) -> Season:
        """Lock the parent plot and reject overlapping rice-season intervals."""
        self.get_plot(data.plot_id, lock=True)
        validate_season_dates(data.start_date, data.end_date)
        if any(
            seasons_overlap(data.start_date, data.end_date, other)
            for other in self.repository.seasons_for_plot(data.plot_id)
        ):
            raise FarmConflict("SEASON_OVERLAP", "该地块已有重叠种植季，请先结束上一季或核对日期")
        season = Season(
            uuid4(),
            data.plot_id,
            data.start_date,
            data.establishment_method,
            data.variety_name.strip() or None if data.variety_name else None,
            data.end_date,
            datetime.now(UTC),
        )
        self.repository.add_season(season)
        return season

    def list_seasons(self, plot_id: UUID, limit: int, offset: int) -> Page[Season]:
        """Reject a missing plot before returning its season page."""
        self.get_plot(plot_id)
        return self.repository.list_seasons(plot_id, limit, offset)

    def close_season(self, season_id: UUID, end_date: date) -> Season:
        """End a season after its current operations, preserving completed seasons."""
        initial = self.get_season(season_id)
        self.get_plot(initial.plot_id, lock=True)
        season = self.get_season(season_id, lock=True)
        if season.end_date is not None:
            if season.end_date == end_date:
                return season
            raise FarmConflict("SEASON_ALREADY_CLOSED", "该季已结束，不能重新修改结束日期")
        validate_season_dates(season.start_date, end_date)
        if self.repository.has_current_event_after(season_id, end_date):
            raise FarmError("END_BEFORE_EVENT", "结束日期不能早于已登记的有效农事")
        self.repository.close_season(season_id, end_date)
        return replace(season, end_date=end_date)

    def create_event(self, season_id: UUID, data: EventInput) -> ManagementEvent:
        """Append an operation under a locked season, checking dates and quantities."""
        season = self.get_season(season_id, lock=True)
        event = self._build_event(season, data)
        self.repository.add_event(event)
        return event

    def correct_event(self, event_id: UUID, data: EventInput, reason: str) -> ManagementEvent:
        """Append exactly one successor to the current operation revision."""
        previous = self.repository.get_event(event_id)
        if previous is None:
            raise FarmNotFound("EVENT_NOT_FOUND", "找不到该农事记录")
        season = self.get_season(previous.season_id, lock=True)
        previous = self.repository.get_event(event_id)
        if previous is None or not previous.is_current:
            raise FarmConflict("STALE_REVISION", "此记录已被修正，请刷新后选择最新记录")
        if not reason.strip() or len(reason.strip()) > 240:
            raise FarmError("CORRECTION_REASON_REQUIRED", "请填写 1–240 字的修正原因")
        event = replace(
            self._build_event(season, data),
            revision=previous.revision + 1,
            replaces_event_id=previous.id,
            correction_reason=reason.strip(),
        )
        self.repository.add_event(event)
        return event

    def list_events(
        self, season_id: UUID, limit: int, offset: int, *, include_history: bool = False
    ) -> Page[ManagementEvent]:
        """Return current operations by default, or all retained revisions."""
        self.get_season(season_id)
        return self.repository.list_events(
            season_id, limit, offset, include_history=include_history
        )

    def _build_event(self, season: Season, data: EventInput) -> ManagementEvent:
        validate_event_date(data.occurred_on, season)
        plot = self.get_plot(season.plot_id)
        quantity, unit = normalize_event_quantity(data, plot.area_ha)
        return ManagementEvent(
            id=uuid4(),
            season_id=season.id,
            event_type=data.event_type,
            occurred_on=data.occurred_on,
            quantity=data.quantity,
            unit=data.unit,
            normalized_quantity=quantity,
            normalized_unit=unit,
            material_name=data.material_name.strip() if data.material_name else None,
            notes=data.notes.strip(),
            created_at=datetime.now(UTC),
        )
