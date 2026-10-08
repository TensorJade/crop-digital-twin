"""Prepare and freeze scientific inputs without executing a model in an API request."""

import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from crop_engine.inputs import (
    InputDataError,
    InputReport,
    Issue,
    ParameterValue,
    WeatherDay,
    canonical_json,
    check_inputs,
    content_hash,
    parse_weather_csv,
    pcse_weather_fields,
)

from crop_twin import __version__
from crop_twin.application.farm_service import FarmService
from crop_twin.application.input_repository import InputRepository
from crop_twin.domain.farm.models import ManagementEvent, Plot, Season
from crop_twin.domain.farm.rules import FarmError, FarmNotFound
from crop_twin.domain.identity.models import User
from crop_twin.domain.pagination import Page
from crop_twin.domain.simulation.models import (
    AssetInput,
    AssetKind,
    InputAsset,
    SimulationInput,
    SnapshotInput,
)


def portable_record(record: Plot | Season | ManagementEvent | InputAsset) -> dict[str, Any]:
    """Preserve dates/Decimals/UUIDs as portable strings, never binary Python objects."""
    return cast(dict[str, Any], json.loads(json.dumps(asdict(record), default=str)))


class SimulationInputService:
    """Input and farm adapters share a single caller-owned, scoped SQL transaction."""

    def __init__(self, repository: InputRepository, farm: FarmService, actor: User) -> None:
        self.repository, self.farm, self.actor = repository, farm, actor

    def create_asset(self, data: AssetInput) -> InputAsset:
        """Persist one typed input version and its audit; weather gaps remain explicit."""
        if data.kind != "crop":
            if data.plot_id is None:
                raise FarmError("INPUT_PLOT_REQUIRED", "土壤与天气资料需要选择地块")
            self.farm.get_plot(data.plot_id)
        elif data.plot_id is not None:
            raise FarmError("CROP_SCOPE_INVALID", "品种参数保存在本组织，不指定地块")
        payload = dict(data.payload)
        if data.kind == "weather":
            try:
                payload["days"] = parse_weather_csv(payload["csv_text"])
            except InputDataError as error:
                raise FarmError("INVALID_WEATHER_CSV", str(error)) from None
        # A predictable bound protects both SQL storage and later JSON snapshot downloads.
        if len(canonical_json(payload).encode("utf-8")) > 524288:
            raise FarmError("INPUT_TOO_LARGE", "单份输入资料最多 512 KiB")
        asset = InputAsset(
            uuid4(),
            self.actor.organization_id,
            data.plot_id,
            data.kind,
            data.name,
            data.source,
            data.source_license,
            payload,
            content_hash(payload),
            self.actor.id,
            datetime.now(UTC),
        )
        self.repository.add_asset(asset)
        self.farm.repository.record_audit("inputs.asset_created", "input_asset", asset.id)
        return asset

    def get_asset(self, asset_id: UUID) -> InputAsset:
        """Read only the team's input version."""
        asset = self.repository.get_asset(asset_id)
        if asset is None:
            raise FarmNotFound("INPUT_ASSET_NOT_FOUND", "找不到该输入资料")
        return asset

    def list_assets(
        self, kind: AssetKind, plot_id: UUID | None, limit: int, offset: int
    ) -> Page[InputAsset]:
        """List the crop library or plot-specific soil/weather metadata."""
        if kind != "crop":
            if plot_id is None:
                raise FarmError("INPUT_PLOT_REQUIRED", "请选择地块后读取土壤与天气资料")
            self.farm.get_plot(plot_id)
        elif plot_id is not None:
            raise FarmError("CROP_SCOPE_INVALID", "品种参数按本组织查询，不指定地块")
        return self.repository.list_assets(kind, plot_id, limit, offset)

    def prepare(self, data: SnapshotInput) -> dict[str, Any]:
        """Freeze latest management revisions under the season lock, without writing a record."""
        season = self.farm.get_season(data.season_id, lock=True)
        plot = self.farm.get_plot(season.plot_id)
        if not data.emergence_date <= data.cutoff_date <= date.today():
            raise FarmError("INPUT_DATES_INVALID", "出苗日期应不晚于截止日期，截止日期不能是未来")
        if (data.cutoff_date - data.emergence_date).days >= 366:
            raise FarmError("INPUT_PERIOD_TOO_LONG", "一次快照最多包含 366 天")
        if data.cutoff_date < season.start_date or (
            season.end_date and data.cutoff_date > season.end_date
        ):
            raise FarmError("INPUT_OUTSIDE_SEASON", "截止日期应位于种植季内")
        if (
            season.establishment_method == "direct_sowing"
            and data.emergence_date < season.start_date
        ):
            raise FarmError("EMERGENCE_BEFORE_SOWING", "直播的出苗日期不能早于播种日期")
        if (
            season.establishment_method == "transplanting"
            and data.emergence_date > season.start_date
        ):
            raise FarmError("EMERGENCE_AFTER_TRANSPLANT", "移栽的出苗日期应不晚于移栽日期")
        assets = [
            self.get_asset(asset_id)
            for asset_id in (data.soil_asset_id, data.crop_asset_id, data.weather_asset_id)
        ]
        for asset, kind in zip(assets, ("soil", "crop", "weather"), strict=True):
            if asset.kind != kind or (kind != "crop" and asset.plot_id != plot.id):
                raise FarmNotFound("INPUT_ASSET_NOT_FOUND", "所选资料不属于当前地块或类型不正确")
        soil, crop, weather = assets
        parameters = cast(dict[str, ParameterValue], crop.payload["parameters"])
        days = cast(list[WeatherDay], weather.payload["days"])
        report = check_inputs(
            parameters, days, data.emergence_date, data.cutoff_date, season.establishment_method
        )
        if not -300 <= weather.payload["elevation_m"] <= 6000:
            report["blocking_issues"].append(
                Issue(
                    code="PCSE_ELEVATION_RANGE",
                    message="天气来源海拔超出 PCSE 标准范围，原值已保留，请核对",
                )
            )
        if season.variety_name and crop.payload["variety_name"] != season.variety_name:
            report["blocking_issues"].append(
                Issue(
                    code="VARIETY_MISMATCH", message="所选品种与种植季名称不同，请核对参数对应关系"
                )
            )
        if weather.payload["source_kind"] == "gridded":
            report["warnings"].append(
                Issue(code="GRIDDED_WEATHER", message="这份天气为网格数据，不是本地气象站观测")
            )
        if weather.payload["time_basis"] != "Asia/Shanghai":
            report["warnings"].append(
                Issue(
                    code="WEATHER_DAY_BASIS",
                    message="天气日界采用 UTC 或太阳时，需核对与农事日期的对应",
                )
            )
        if (
            abs(weather.payload["latitude"] - plot.latitude) > 0.5
            or abs(weather.payload["longitude"] - plot.longitude) > 0.5
        ):
            report["warnings"].append(
                Issue(code="WEATHER_LOCATION", message="天气来源位置与地块差异较大，请核对代表性")
            )
        report["input_ready"] = not report["blocking_issues"]
        events = self.farm.list_events(season.id, limit=5001, offset=0)
        if events.total > 5000:
            raise FarmError(
                "TOO_MANY_MANAGEMENT_EVENTS", "单季有效农事超过 5000 条，请核对后再保存快照"
            )
        included = [event for event in events.items if event.occurred_on <= data.cutoff_date]
        return {
            "schema_version": "1.0.0",
            "software_version": __version__,
            "model_target": "WOFOST72",
            "simulation_executed": False,
            "period": {
                "emergence_date": data.emergence_date.isoformat(),
                "cutoff_date": data.cutoff_date.isoformat(),
            },
            "plot": portable_record(plot),
            "season": portable_record(season),
            "assets": {asset.kind: portable_record(asset) for asset in assets},
            "management_events": [portable_record(event) for event in included],
            "pcse_fields": {
                "soil": {
                    "SMW": soil.payload["wilting_point"],
                    "SMFCF": soil.payload["field_capacity"],
                    "SM0": soil.payload["saturation"],
                    "RDMSOL": soil.payload["depth_cm"],
                },
                "weather": [
                    pcse_weather_fields(day)
                    for day in days
                    if data.emergence_date.isoformat()
                    <= day["date"]
                    <= data.cutoff_date.isoformat()
                ],
            },
            "report": report,
        }

    def check(self, data: SnapshotInput) -> InputReport:
        """Preview all missing inputs without creating a version or audit."""
        return cast(InputReport, self.prepare(data)["report"])

    def create_snapshot(self, data: SnapshotInput) -> SimulationInput:
        """Save even incomplete data explicitly as an input snapshot, never a simulation result."""
        payload = self.prepare(data)
        if len(canonical_json(payload).encode("utf-8")) > 1048576:
            raise FarmError("SNAPSHOT_TOO_LARGE", "单份快照最多 1 MiB，请缩短天气范围或简化资料")
        snapshot = SimulationInput(
            uuid4(),
            self.actor.organization_id,
            data.season_id,
            self.repository.next_version(data.season_id),
            payload,
            content_hash(payload),
            self.actor.id,
            datetime.now(UTC),
        )
        self.repository.add_snapshot(snapshot)
        self.farm.repository.record_audit(
            "inputs.snapshot_created", "simulation_input", snapshot.id
        )
        return snapshot

    def get_snapshot(self, input_id: UUID) -> SimulationInput:
        """Read one immutable team snapshot for export."""
        snapshot = self.repository.get_snapshot(input_id)
        if snapshot is None:
            raise FarmNotFound("SIMULATION_INPUT_NOT_FOUND", "找不到该输入快照")
        return snapshot

    def list_snapshots(self, season_id: UUID, limit: int, offset: int) -> Page[SimulationInput]:
        """Only a season visible to the team can expose its input versions."""
        self.farm.get_season(season_id)
        return self.repository.list_snapshots(season_id, limit, offset)
