"""NASA POWER hourly data to declared UTC+8 daily grid weather; never station data."""

import csv
import io
import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from crop_engine.inputs import InputDataError, canonical_json, content_hash, parse_weather_csv

POWER_PARAMETERS = ("T2M", "T2MDEW", "WS2M", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN")
POWER_LIMIT = 393216
ADAPTER_VERSION = "1.0.0"
POWER_LICENSE = "NASA公开科学数据；保留POWER来源，按NASA数据许可政策和访问条款使用"
POWER_SOURCE = "NASA POWER / MERRA-2与卫星辐射历史网格天气"


def check_period(start: date, end: date) -> None:
    """Allow 1–120 complete past Beijing days; do not synthesize today's weather."""
    today = (datetime.now(UTC) + timedelta(hours=8)).date()
    if start < date(2001, 1, 2) or not start <= end < today or (end - start).days >= 120:
        raise InputDataError("日期应为2001-01-02起、已结束的1–120天")


def aggregate_power(raw: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    """Require 24 finite values per day and preserve raw units instead of guessing them."""
    check_period(start, end)
    try:
        if len(canonical_json(raw).encode("utf-8")) > POWER_LIMIT:
            raise ValueError("Oversized raw response")
        if raw["header"]["time_standard"] != "UTC":
            raise ValueError("Unexpected time standard")
        units = {name: raw["parameters"][name]["units"] for name in POWER_PARAMETERS}
        expected = ("C", "C", "m/s", "mm/hour", "MJ/hr")
        if tuple(units[name] for name in POWER_PARAMETERS) != expected:
            raise ValueError("Unexpected provider units")
        coordinates = raw["geometry"]["coordinates"]
        lon, lat, elevation = (float(value) for value in coordinates)
        if not all(math.isfinite(value) for value in (lat, lon, elevation)):
            raise ValueError("Nonfinite source position")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180 or not -300 <= elevation <= 6000:
            raise ValueError("Source position out of model bounds")
        series = raw["properties"]["parameter"]
        fill = raw["header"]["fill_value"]
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(
            ("date", "tmin_c", "tmax_c", "rain_mm", "radiation_mj_m2", "wind_m_s", "vapor_kpa")
        )
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            hours: dict[str, list[float]] = {name: [] for name in POWER_PARAMETERS}
            for hour in range(24):
                stamp = datetime.combine(day, datetime.min.time()) + timedelta(hours=hour - 8)
                key = stamp.strftime("%Y%m%d%H")
                for name in POWER_PARAMETERS:
                    value = series[name][key]
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise ValueError("Non-numeric hourly data")
                    if not math.isfinite(value) or value == fill:
                        raise ValueError("Missing hourly data")
                    lower, upper = {
                        "T2M": (-80, 65),
                        "T2MDEW": (-80, 65),
                        "WS2M": (0, 100),
                        "PRECTOTCORR": (0, 500),
                        "ALLSKY_SFC_SW_DWN": (0, 6),
                    }[name]
                    if not lower <= value <= upper:
                        raise ValueError("Hourly value outside declared bounds")
                    hours[name].append(float(value))
            if any(
                dew > temp + 0.2 for dew, temp in zip(hours["T2MDEW"], hours["T2M"], strict=True)
            ):
                raise ValueError("Dew point exceeds air temperature")
            vapor = (
                sum(0.6108 * math.exp(17.27 * value / (value + 237.3)) for value in hours["T2MDEW"])
                / 24
            )
            values = [
                min(hours["T2M"]),
                max(hours["T2M"]),
                sum(hours["PRECTOTCORR"]),
                sum(hours["ALLSKY_SFC_SW_DWN"]),
                sum(hours["WS2M"]) / 24,
                vapor,
            ]
            writer.writerow([day.isoformat(), *(round(value, 6) for value in values)])
        text = buffer.getvalue()
        days = parse_weather_csv(text)
        return {
            "source_kind": "gridded",
            "station_id": None,
            "latitude": lat,
            "longitude": lon,
            "elevation_m": elevation,
            "wind_height_m": 2,
            "time_basis": "Asia/Shanghai",
            "angstrom_a": None,
            "angstrom_b": None,
            "csv_text": text,
            "days": days,
        }
    except (KeyError, ValueError, TypeError, OverflowError, InputDataError):
        raise InputDataError("NASA小时资料缺测、单位变化或超出范围，未生成替代天气") from None


def validate_power_provenance(payload: dict[str, Any]) -> None:
    """Recompute saved grid data from the sealed response; hashes do not prove authenticity."""
    provenance = payload.get("provider")
    if provenance is None:
        return
    try:
        if provenance["adapter_version"] != ADAPTER_VERSION:
            raise ValueError("Unsupported adapter")
        start, end = (
            date.fromisoformat(provenance["start_date"]),
            date.fromisoformat(provenance["end_date"]),
        )
        raw = provenance["raw_response"]
        if content_hash(raw) != provenance["raw_hash"]:
            raise ValueError("Raw hash mismatch")
        derived = aggregate_power(raw, start, end)
        for field in (
            "source_kind",
            "station_id",
            "latitude",
            "longitude",
            "elevation_m",
            "wind_height_m",
            "time_basis",
            "csv_text",
        ):
            if payload[field] != derived[field]:
                raise ValueError("Derived data was changed")
        if abs(payload["latitude"] - provenance["requested_latitude"]) > 0.001:
            raise ValueError("Request latitude mismatch")
        if abs(payload["longitude"] - provenance["requested_longitude"]) > 0.001:
            raise ValueError("Request longitude mismatch")
    except (KeyError, ValueError, TypeError, InputDataError):
        raise InputDataError("天气来源快照或逐日转换校验不一致，请重新获取") from None
