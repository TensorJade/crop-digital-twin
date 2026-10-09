"""Coordinate fixed transport, provenance and a small station-catalogue cache."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Any

from crop_engine.inputs import InputDataError, content_hash

from crop_twin.domain.farm.models import Plot
from crop_twin.domain.simulation.weather import WeatherUnavailable
from crop_twin.infrastructure.weather.http import POWER_ENDPOINT, STATION_ENDPOINT, WeatherHttp
from crop_twin.infrastructure.weather.power import (
    ADAPTER_VERSION,
    POWER_LICENSE,
    POWER_LIMIT,
    POWER_PARAMETERS,
    POWER_SOURCE,
    aggregate_power,
    check_period,
    validate_power_provenance,
)
from crop_twin.infrastructure.weather.stations import nearby_stations


class WeatherSources:
    """On-demand previews; the existing input service owns persistence and permissions."""

    def __init__(self, http: WeatherHttp | None = None) -> None:
        self.http = http or WeatherHttp()
        self._cache: tuple[float, str, str, str] | None = None
        self._cache_lock = Lock()

    def preview(self, plot: Plot, start: date, end: date) -> dict[str, Any]:
        """Fetch raw UTC hours and a normalized candidate; saving is a separate POST."""
        check_period(start, end)
        query = {
            "parameters": ",".join(POWER_PARAMETERS),
            "community": "AG",
            "latitude": str(plot.latitude),
            "longitude": str(plot.longitude),
            "start": (start - timedelta(days=1)).strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": "UTC",
        }
        data = self.http.get(POWER_ENDPOINT, query, POWER_LIMIT)
        try:
            raw = json.loads(data)
            weather = aggregate_power(raw, start, end)
        except (ValueError, TypeError, UnicodeError, InputDataError):
            raise WeatherUnavailable(
                "WEATHER_DATA_INVALID", "天气源资料不完整或单位变化，请更换日期或导入CSV"
            ) from None
        days = weather.pop("days")
        weather["provider"] = {
            "code": "nasa_power_hourly",
            "adapter_version": ADAPTER_VERSION,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "requested_latitude": plot.latitude,
            "requested_longitude": plot.longitude,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "raw_response": raw,
            "raw_hash": content_hash(raw),
        }
        try:
            validate_power_provenance(weather)
        except InputDataError:
            raise WeatherUnavailable(
                "WEATHER_DATA_INVALID", "天气源返回的位置或转换结果不一致，请稍后重试"
            ) from None
        return {
            "asset": {
                "kind": "weather",
                "plot_id": str(plot.id),
                "name": f"NASA网格天气 {start.isoformat()}–{end.isoformat()}",
                "source": POWER_SOURCE,
                "source_license": POWER_LICENSE,
                "data": weather,
            },
            "day_count": len(days),
            "sample_days": days[:5],
            "warnings": [
                "NASA POWER为历史网格资料，不是附近站点实测；网格海拔不等于农田海拔。",
                "温度极值由小时值计算；露点换算后取平均蒸汽压，不保证当地农艺精度。",
                "通常存在数日数据延迟；缺小时不补零。"
                "保存后仍需来源提供者补充Angstrom A/B才能计算。",
            ],
        }

    def stations(self, plot: Plot) -> dict[str, Any]:
        """Cache the public catalogue for 24h; report candidates without claiming live coverage."""
        with self._cache_lock:
            if self._cache is None or monotonic() - self._cache[0] >= 86400:
                raw = self.http.get(STATION_ENDPOINT, {}, 8388608)
                try:
                    text = raw.decode("utf-8-sig")
                    nearby_stations(text, plot.latitude, plot.longitude)
                except (UnicodeError, InputDataError):
                    raise WeatherUnavailable(
                        "STATION_DATA_INVALID", "站点目录暂不可用，请稍后重试"
                    ) from None
                self._cache = (
                    monotonic(),
                    text,
                    hashlib.sha256(raw).hexdigest(),
                    datetime.now(UTC).isoformat(),
                )
            _, text, digest, retrieved = self._cache
        return {
            "source": "NOAA NCEI ISD station history",
            "source_url": STATION_ENDPOINT,
            "catalog_hash": digest,
            "retrieved_at": retrieved,
            "radius_km": 200,
            "stations": nearby_stations(text, plot.latitude, plot.longitude),
            "notice": "仅为公开目录位置候选；覆盖日期不证明当前活跃或资料完整，尚未接入站点观测。",
        }
