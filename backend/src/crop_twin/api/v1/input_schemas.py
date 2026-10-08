"""Typed, bounded imports: only data, never executable model configuration."""

from datetime import date, datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from crop_engine.inputs import InputDataError, ParameterValue, validate_parameters
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from crop_twin.api.v1.schemas import OutputModel
from crop_twin.domain.simulation.models import AssetKind

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class InputModel(BaseModel):
    """Unknown fields cannot grant ownership or silently supply scientific assumptions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SoilData(InputModel):
    """Volumetric soil water fractions and measured/profile depth in centimetres."""

    wilting_point: Finite = Field(ge=0, lt=1)
    field_capacity: Finite = Field(gt=0, lt=1)
    saturation: Finite = Field(gt=0, le=1)
    depth_cm: Finite = Field(gt=0, le=500)
    sampled_on: date | None = None

    @model_validator(mode="after")
    def check_water_order(self) -> Self:
        """Reject physically inconsistent water contents rather than silently swapping them."""
        if not self.wilting_point < self.field_capacity < self.saturation:
            raise ValueError("土壤应满足萎蔫点 < 田间持水量 < 饱和含水量")
        if self.sampled_on and self.sampled_on > date.today():
            raise ValueError("土壤采样日期不能为未来日期")
        return self


class CropData(InputModel):
    """Only a declared rice parameter set; this is not an agronomic approval."""

    crop_code: Literal["rice"] = "rice"
    model_code: Literal["WOFOST72"] = "WOFOST72"
    variety_name: str = Field(min_length=1, max_length=100)
    applicable_region: str = Field(min_length=1, max_length=200)
    parameters: dict[str, Finite | Annotated[list[Finite], Field(min_length=1, max_length=200)]] = (
        Field(min_length=1, max_length=150)
    )

    @model_validator(mode="after")
    def check_parameter_data(self) -> Self:
        """Use the pure engine input rules, without importing PCSE or a remote provider."""
        try:
            parameters: dict[str, ParameterValue] = dict(self.parameters)
            validate_parameters(parameters)
        except InputDataError as error:
            raise ValueError(str(error)) from None
        return self


class WeatherData(InputModel):
    """CSV unit metadata differentiates a real station from a gridded product."""

    source_kind: Literal["station", "gridded"]
    station_id: str | None = Field(default=None, min_length=1, max_length=80)
    latitude: Finite = Field(ge=-90, le=90)
    longitude: Finite = Field(ge=-180, le=180)
    elevation_m: Finite = Field(ge=-500, le=9000)
    wind_height_m: Literal[2] = 2
    time_basis: Literal["Asia/Shanghai", "UTC", "LST"]
    csv_text: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=1, max_length=262144
    )

    @model_validator(mode="after")
    def check_source_identity(self) -> Self:
        """Do not let gridded weather be labelled as an observed station."""
        if self.source_kind == "station" and not self.station_id:
            raise ValueError("站点天气需要填写气象站编号")
        if self.source_kind == "gridded" and self.station_id is not None:
            raise ValueError("网格天气不填写气象站编号")
        return self


class AssetCreateBase(InputModel):
    """Provenance is required on every input version; source URLs are never fetched."""

    name: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=1000)
    source_license: str = Field(min_length=1, max_length=300)


class SoilAssetCreate(AssetCreateBase):
    """A soil profile belongs to an authenticated team's plot."""

    kind: Literal["soil"]
    plot_id: UUID
    data: SoilData


class CropAssetCreate(AssetCreateBase):
    """A crop parameter version is shared within the current organization."""

    kind: Literal["crop"]
    plot_id: None = None
    data: CropData


class WeatherAssetCreate(AssetCreateBase):
    """Weather is explicitly selected for a plot, with original CSV retained."""

    kind: Literal["weather"]
    plot_id: UUID
    data: WeatherData


type AssetCreate = Annotated[
    SoilAssetCreate | CropAssetCreate | WeatherAssetCreate, Field(discriminator="kind")
]


class AssetSummary(OutputModel):
    """List only metadata; large CSV/parameter payloads require detail access."""

    id: UUID
    organization_id: UUID
    plot_id: UUID | None
    kind: AssetKind
    name: str
    source: str
    source_license: str
    content_hash: str
    actor_user_id: UUID
    created_at: datetime


class AssetResponse(AssetSummary):
    """Return the exact validated payload and hash on detail/create."""

    payload: dict[str, Any]


class SnapshotCreate(InputModel):
    """Dates are explicit; the sowing/transplanting date is not assumed to be emergence."""

    season_id: UUID
    soil_asset_id: UUID
    crop_asset_id: UUID
    weather_asset_id: UUID
    emergence_date: date
    cutoff_date: date


class IssueResponse(BaseModel):
    """A stable preflight code and plain-language next action."""

    code: str
    message: str


class ReportResponse(BaseModel):
    """Completeness cannot be confused with an executed/validated simulation."""

    input_ready: bool
    simulation_available: Literal[False]
    blocking_issues: list[IssueResponse]
    warnings: list[IssueResponse]
    missing_weather_days: int
    missing_parameters: list[str]


class SnapshotSummary(OutputModel):
    """Page snapshot versions and checks without duplicating all scientific inputs."""

    id: UUID
    organization_id: UUID
    season_id: UUID
    version: int
    content_hash: str
    actor_user_id: UUID
    created_at: datetime
    report: ReportResponse


class SnapshotResponse(SnapshotSummary):
    """The complete frozen input can be downloaded as JSON."""

    payload: dict[str, Any]
