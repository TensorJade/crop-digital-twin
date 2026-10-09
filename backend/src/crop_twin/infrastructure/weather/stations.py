"""NOAA station catalogue candidates; this adapter does not fetch their observations."""

import csv
import io
import math
from datetime import date

from crop_engine.inputs import InputDataError


def nearby_stations(text: str, latitude: float, longitude: float) -> list[dict[str, object]]:
    """Rank valid coordinates within 200km, retaining historical coverage as metadata only."""
    try:
        reader = csv.DictReader(io.StringIO(text))
        required = {"USAF", "WBAN", "STATION NAME", "LAT", "LON", "ELEV(M)", "BEGIN", "END"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Unknown station schema")
        found: dict[str, dict[str, object]] = {}
        for row in reader:
            try:
                lat, lon, elevation = float(row["LAT"]), float(row["LON"]), float(row["ELEV(M)"])
                begin, end = date.fromisoformat(row["BEGIN"]), date.fromisoformat(row["END"])
                if not all(math.isfinite(value) for value in (lat, lon, elevation)):
                    continue
                if not -90 <= lat <= 90 or not -180 <= lon <= 180 or begin > end:
                    continue
                a, b = math.radians(latitude), math.radians(lat)
                delta = math.radians(lon - longitude)
                hav = (
                    math.sin((b - a) / 2) ** 2
                    + math.cos(a) * math.cos(b) * math.sin(delta / 2) ** 2
                )
                distance = 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, hav))))
                if distance > 200 or not row["USAF"].isdigit() or not row["WBAN"].isdigit():
                    continue
                station_id = row["USAF"] + "-" + row["WBAN"]
                candidate: dict[str, object] = {
                    "station_id": station_id,
                    "name": row["STATION NAME"].strip(),
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_m": elevation,
                    "distance_km": round(distance, 2),
                    "coverage_start": begin.isoformat(),
                    "coverage_end": end.isoformat(),
                    "observations_connected": False,
                }
                found[station_id] = candidate
            except (KeyError, ValueError, TypeError):
                continue
        return sorted(
            found.values(),
            key=lambda item: (float(str(item["distance_km"])), str(item["station_id"])),
        )[:5]
    except (ValueError, csv.Error, TypeError):
        raise InputDataError("站点目录结构变化，请稍后重试") from None
