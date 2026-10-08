"""Thin farm HTTP adapters with one committed transaction per request."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from crop_twin.api.v1.dependencies import DatabaseDependency, PrincipalDependency
from crop_twin.api.v1.farm_schemas import (
    ErrorResponse,
    EventCorrection,
    EventCreate,
    EventResponse,
    PageResponse,
    PlotCreate,
    PlotResponse,
    SeasonClose,
    SeasonCreate,
    SeasonResponse,
)
from crop_twin.application.farm_service import FarmService
from crop_twin.domain.farm.models import EventInput, PlotInput, SeasonInput
from crop_twin.domain.identity.rules import require_writer
from crop_twin.infrastructure.database.farm_repository import SqlFarmRepository

router = APIRouter(
    prefix="/api/v1",
    tags=["farm"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 503)},
)


def get_farm_service(
    request: Request, session: DatabaseDependency, principal: PrincipalDependency
) -> Iterator[FarmService]:
    """Commit before sending a response; roll back failed/stale farm operations."""
    if request.method == "POST":
        require_writer(principal.user)
    repository = SqlFarmRepository(session, principal.user.organization_id, principal.user.id)
    yield FarmService(repository, principal.user.organization_id)


FarmDependency = Annotated[FarmService, Depends(get_farm_service, scope="function")]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/plots", response_model=PageResponse[PlotResponse], operation_id="listPlots")
def list_plots(service: FarmDependency, limit: Limit = 50, offset: Offset = 0) -> object:
    """Page saved plots in newest-first order."""
    return service.list_plots(limit, offset)


@router.post("/plots", response_model=PlotResponse, status_code=201, operation_id="createPlot")
def create_plot(data: PlotCreate, service: FarmDependency) -> object:
    """Save a manual plot with its original area and position."""
    return service.create_plot(PlotInput(**data.model_dump()))


@router.get("/plots/{plot_id}", response_model=PlotResponse, operation_id="getPlot")
def get_plot(plot_id: UUID, service: FarmDependency) -> object:
    """Read one plot, or return a documented 404."""
    return service.get_plot(plot_id)


@router.get("/seasons", response_model=PageResponse[SeasonResponse], operation_id="listSeasons")
def list_seasons(
    plot_id: UUID, service: FarmDependency, limit: Limit = 50, offset: Offset = 0
) -> object:
    """Page rice seasons belonging to one plot."""
    return service.list_seasons(plot_id, limit, offset)


@router.post(
    "/seasons", response_model=SeasonResponse, status_code=201, operation_id="createSeason"
)
def create_season(data: SeasonCreate, service: FarmDependency) -> object:
    """Establish a non-overlapping rice season."""
    return service.create_season(SeasonInput(**data.model_dump()))


@router.post(
    "/seasons/{season_id}/close", response_model=SeasonResponse, operation_id="closeSeason"
)
def close_season(season_id: UUID, data: SeasonClose, service: FarmDependency) -> object:
    """Confirm season completion after all still-current operations."""
    return service.close_season(season_id, data.end_date)


@router.get(
    "/management-events",
    response_model=PageResponse[EventResponse],
    operation_id="listManagementEvents",
)
def list_events(
    season_id: UUID,
    service: FarmDependency,
    limit: Limit = 50,
    offset: Offset = 0,
    include_history: bool = False,
) -> object:
    """Page the current operation versions, or include retained history."""
    return service.list_events(season_id, limit, offset, include_history=include_history)


@router.post(
    "/management-events",
    response_model=EventResponse,
    status_code=201,
    operation_id="createManagementEvent",
)
def create_event(data: EventCreate, service: FarmDependency) -> object:
    """Save an operation with original and standard-unit quantities."""
    return service.create_event(
        data.season_id, EventInput(**data.model_dump(exclude={"season_id"}))
    )


@router.post(
    "/management-events/{event_id}/corrections",
    response_model=EventResponse,
    status_code=201,
    operation_id="correctManagementEvent",
)
def correct_event(event_id: UUID, data: EventCorrection, service: FarmDependency) -> object:
    """Append a corrected operation without overwriting its predecessor."""
    return service.correct_event(
        event_id,
        EventInput(**data.model_dump(exclude={"correction_reason"})),
        data.correction_reason,
    )
