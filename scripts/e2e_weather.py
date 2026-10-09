"""Synthetic fixed-format responses, used only by the guarded browser test launcher."""

import json
from datetime import date
from pathlib import Path
from typing import Any

from crop_twin.domain.farm.models import Plot
from crop_twin.infrastructure.weather.http import POWER_ENDPOINT, STATION_ENDPOINT, WeatherHttp
from crop_twin.infrastructure.weather.sources import WeatherSources

ROOT = Path(__file__).resolve().parents[1]


class FixtureWeatherHttp(WeatherHttp):
    """Test transport never contacts NASA/NOAA; fixtures are explicitly self-created."""

    def get(self, endpoint: str, parameters: dict[str, str], limit: int) -> bytes:
        """Return bounded fixture bytes using the same parser as the actual provider."""
        if endpoint == POWER_ENDPOINT:
            raw = json.loads(
                (ROOT / "tests/fixtures/power-hourly.json").read_text(encoding="utf-8")
            )
            raw["geometry"]["coordinates"][:2] = [
                float(parameters["longitude"]),
                float(parameters["latitude"]),
            ]
            return json.dumps(raw).encode("utf-8")
        if endpoint == STATION_ENDPOINT:
            return (ROOT / "tests/fixtures/weather-stations.csv").read_bytes()
        raise ValueError("Unknown test weather source")


class FixtureWeatherSources(WeatherSources):
    """The test label is set at injection, without a production environment switch."""

    def __init__(self) -> None:
        super().__init__(FixtureWeatherHttp())

    def preview(self, plot: Plot, start: date, end: date) -> dict[str, Any]:
        """Use the real transformation, clearly identifying the self-created test source."""
        result = super().preview(plot, start, end)
        result["asset"]["source"] = "软件验收合成响应（格式参考NASA POWER，非真实天气）"
        result["asset"]["source_license"] = "自有合成资料，仅软件验收"
        return result
