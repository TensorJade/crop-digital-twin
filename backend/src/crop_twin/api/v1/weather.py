"""Weather previews release their scoped SQL transaction before external HTTP."""

from datetime import date
from typing import Annotated, Any, cast
from uuid import UUID

from crop_engine.inputs import InputDataError
from fastapi import APIRouter, Depends, Request, Security
from pydantic import BaseModel

from crop_twin.api.v1.dependencies import current_principal, session_cookie, session_factory
from crop_twin.api.v1.input_schemas import WeatherAssetCreate
from crop_twin.api.v1.schemas import ErrorResponse
from crop_twin.application.farm_service import FarmService
from crop_twin.domain.farm.models import Plot
from crop_twin.domain.farm.rules import FarmError
from crop_twin.domain.identity.rules import require_writer
from crop_twin.infrastructure.database.farm_repository import SqlFarmRepository
from crop_twin.infrastructure.weather.sources import WeatherSources

router = APIRouter(
    prefix="/api/v1/weather",
    tags=["weather"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 503)},
)


class WeatherPreview(BaseModel):
    """An unsaved candidate with raw provenance; no inferred Angstrom defaults."""

    asset: WeatherAssetCreate
    day_count: int
    sample_days: list[dict[str, Any]]
    warnings: list[str]


class StationCandidate(BaseModel):
    """Public catalogue position and coverage; observation access is still separate."""

    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation_m: float
    distance_km: float
    coverage_start: date
    coverage_end: date
    observations_connected: bool


class StationList(BaseModel):
    """Metadata and catalogue version for a nearby-station search."""

    source: str
    source_url: str
    catalog_hash: str
    retrieved_at: str
    radius_km: int
    stations: list[StationCandidate]
    notice: str


def weather_plot(
    request: Request,
    plot_id: UUID,
    token: Annotated[str | None, Security(session_cookie)],
) -> Plot:
    """Authenticate and resolve a writer's own plot, then close SQL before fetching."""
    with session_factory(request).begin() as session:
        principal = current_principal(request, session, token)
        require_writer(principal.user)
        organization_id = principal.user.organization_id
        farm = FarmService(
            SqlFarmRepository(session, organization_id, principal.user.id), organization_id
        )
        return farm.get_plot(plot_id)


WeatherPlot = Annotated[Plot, Depends(weather_plot)]


@router.get("/preview", response_model=WeatherPreview, operation_id="previewGridWeather")
def preview(request: Request, plot: WeatherPlot, start_date: date, end_date: date) -> object:
    """Fetch declared historical weather for the scoped coordinates; no data is written."""
    sources = cast(WeatherSources, request.app.state.weather_sources)
    try:
        return sources.preview(plot, start_date, end_date)
    except InputDataError as error:
        raise FarmError("WEATHER_PERIOD_INVALID", str(error)) from None


@router.get("/stations", response_model=StationList, operation_id="listNearbyWeatherStations")
def stations(request: Request, plot: WeatherPlot) -> object:
    """Search the real public station catalogue; grid data is never attached to a station."""
    return cast(WeatherSources, request.app.state.weather_sources).stations(plot)
