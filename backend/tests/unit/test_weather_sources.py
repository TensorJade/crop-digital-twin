"""Network-independent checks for time boundaries, units, provenance and catalogue search."""

import io
import json
import math
from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest
from crop_engine.inputs import InputDataError, content_hash
from crop_twin.domain.farm.models import Plot
from crop_twin.domain.simulation.weather import WeatherUnavailable
from crop_twin.infrastructure.weather import http as transport
from crop_twin.infrastructure.weather.power import (
    aggregate_power,
    check_period,
    validate_power_provenance,
)
from crop_twin.infrastructure.weather.sources import WeatherSources
from crop_twin.infrastructure.weather.stations import nearby_stations

FIXTURES = Path(__file__).resolve().parents[3] / "tests/fixtures"
START, END = date(2024, 3, 2), date(2024, 3, 3)


def raw_weather():
    return json.loads((FIXTURES / "power-hourly.json").read_text(encoding="utf-8"))


def plot():
    return Plot(
        id=uuid4(),
        organization_id=uuid4(),
        name="天气软件验收田",
        area_mu=Decimal("15"),
        latitude=23.1,
        longitude=113.2,
        created_at=datetime.now(UTC),
    )


class FixtureHttp(transport.WeatherHttp):
    def __init__(self):
        super().__init__()
        self.calls = []

    def get(self, endpoint, parameters, limit):
        self.calls.append((endpoint, parameters, limit))
        path = (
            "power-hourly.json" if endpoint == transport.POWER_ENDPOINT else "weather-stations.csv"
        )
        return (FIXTURES / path).read_bytes()


def test_utc_to_beijing_uses_previous_day_and_all_24_hours_without_future_tail():
    raw = raw_weather()
    raw["properties"]["parameter"]["T2M"]["2024030116"] = 35.0
    raw["properties"]["parameter"]["T2M"]["2024030316"] = -999.0
    result = aggregate_power(raw, START, END)
    assert result["source_kind"] == "gridded" and result["station_id"] is None
    assert result["time_basis"] == "Asia/Shanghai"
    assert [day["date"] for day in result["days"]] == ["2024-03-02", "2024-03-03"]
    first = result["days"][0]
    assert first["tmax_c"] == 35 and first["tmin_c"] == 20
    assert first["rain_mm"] == 2.4 and first["radiation_mj_m2"] == 12
    assert first["wind_m_s"] == 2
    assert first["vapor_kpa"] == pytest.approx(0.6108 * math.exp(17.27 * 12 / 249.3), abs=1e-6)


@pytest.mark.parametrize(
    "cause",
    [
        "missing",
        "fill",
        "bool",
        "null",
        "nan",
        "negative",
        "units",
        "time",
        "geometry",
        "dew",
        "oversize",
    ],
)
def test_bad_hour_or_changed_provider_contract_rejects_entire_candidate(cause):
    raw = raw_weather()
    row = raw["properties"]["parameter"]["T2M"]
    if cause == "missing":
        del row["2024030116"]
    elif cause == "units":
        raw["parameters"]["ALLSKY_SFC_SW_DWN"]["units"] = "W/m2"
    elif cause == "time":
        raw["header"]["time_standard"] = "LST"
    elif cause == "geometry":
        raw["geometry"]["coordinates"][2] = 7000
    elif cause == "dew":
        raw["properties"]["parameter"]["T2MDEW"]["2024030116"] = 40
    elif cause == "oversize":
        raw["unused"] = "x" * 393217
    elif cause == "negative":
        raw["properties"]["parameter"]["PRECTOTCORR"]["2024030116"] = -1
    else:
        row["2024030116"] = {"fill": -999, "bool": True, "null": None, "nan": float("nan")}[cause]
    with pytest.raises(InputDataError, match="未生成替代天气"):
        aggregate_power(raw, START, END)


@pytest.mark.parametrize(
    "start,end",
    [(date(2001, 1, 1), END), (END, START), (START, date(2024, 7, 1)), (START, date(2099, 1, 1))],
)
def test_complete_past_period_and_length_are_explicit(start, end):
    with pytest.raises(InputDataError):
        check_period(start, end)


def test_provenance_recomputes_csv_hash_and_request_coordinates_without_filling_coefficients():
    client = FixtureHttp()
    preview = WeatherSources(client).preview(plot(), START, END)
    data = preview["asset"]["data"]
    assert data["angstrom_a"] is None and preview["day_count"] == 2
    assert client.calls[0][1]["start"] == "20240301"
    assert client.calls[0][1]["time-standard"] == "UTC"
    assert data["provider"]["raw_hash"] == content_hash(data["provider"]["raw_response"])
    validate_power_provenance(data)
    validate_power_provenance({"provider": None})
    for change in ("hash", "csv", "coordinate", "version"):
        altered = deepcopy(data)
        if change == "hash":
            altered["provider"]["raw_hash"] = "0" * 64
        elif change == "csv":
            altered["csv_text"] = altered["csv_text"].replace("2.4", "0.0")
        elif change == "coordinate":
            altered["provider"]["requested_latitude"] = 24
        else:
            altered["provider"]["adapter_version"] = "unknown"
        with pytest.raises(InputDataError):
            validate_power_provenance(altered)


def test_station_candidates_sorted_with_coverage_not_claimed_as_connected_observations():
    text = (FIXTURES / "weather-stations.csv").read_text(encoding="utf-8")
    result = nearby_stations(text, 23.1, 113.2)
    assert [item["station_id"] for item in result] == ["592001-99999", "592002-99999"]
    assert result[0]["distance_km"] == pytest.approx(11.12, abs=0.01)
    assert result[0]["observations_connected"] is False
    assert result[0]["coverage_end"] == "2025-08-24"
    assert nearby_stations(text, -50, -80) == []
    text += "999999,99999,BAD,CH,,,nan,113.2,10,20010101,20250824\n"
    text += "999999,99999,BAD,CH,,,not-a-number,113.2,10,20010101,20250824\n"
    assert len(nearby_stations(text, 23.1, 113.2)) == 2
    with pytest.raises(InputDataError):
        nearby_stations("unexpected,header\n1,2", 23.1, 113.2)


def test_catalogue_cache_reuses_version_and_refreshes_expired_source():
    http = FixtureHttp()
    source = WeatherSources(http)
    first = source.stations(plot())
    assert source.stations(plot())["catalog_hash"] == first["catalog_hash"]
    assert len(http.calls) == 1
    source._cache = (source._cache[0] - 86401, *source._cache[1:])
    source.stations(plot())
    assert len(http.calls) == 2


@pytest.mark.parametrize("response", [b"not json", b"{}", b"[]"])
def test_provider_failures_are_safe(response):
    class BadHttp(FixtureHttp):
        def get(self, endpoint, parameters, limit):
            return response

    with pytest.raises(WeatherUnavailable) as failure:
        WeatherSources(BadHttp()).preview(plot(), START, END)
    assert failure.value.code == "WEATHER_DATA_INVALID"
    with pytest.raises(WeatherUnavailable):
        WeatherSources(BadHttp()).stations(plot())


def test_wrong_source_coordinates_and_unreadable_catalogue_are_rejected():
    class MismatchedHttp(FixtureHttp):
        def get(self, endpoint, parameters, limit):
            if endpoint == transport.STATION_ENDPOINT:
                return b"\xff"
            raw = raw_weather()
            raw["geometry"]["coordinates"][1] = 25
            return json.dumps(raw).encode()

    source = WeatherSources(MismatchedHttp())
    with pytest.raises(WeatherUnavailable) as error:
        source.preview(plot(), START, END)
    assert error.value.code == "WEATHER_DATA_INVALID"
    with pytest.raises(WeatherUnavailable) as error:
        source.stations(plot())
    assert error.value.code == "STATION_DATA_INVALID"


def test_transport_fixed_targets_limits_redirects_and_releases_slots(monkeypatch):
    class Response(io.BytesIO):
        pass

    class Opener:
        def open(self, request, timeout):
            assert request.full_url.startswith(transport.POWER_ENDPOINT)
            assert timeout == 15
            return Response(b"12345")

    monkeypatch.setattr(transport, "build_opener", lambda *args: Opener())
    http = transport.WeatherHttp()
    assert http.get(transport.POWER_ENDPOINT, {"time-standard": "UTC"}, 5) == b"12345"
    with pytest.raises(WeatherUnavailable, match="过大"):
        http.get(transport.POWER_ENDPOINT, {}, 4)
    with pytest.raises(ValueError):
        http.get("http://127.0.0.1/private", {}, 10)
    http._slots.acquire()
    http._slots.acquire()
    try:
        with pytest.raises(WeatherUnavailable) as error:
            http.get(transport.POWER_ENDPOINT, {}, 10)
        assert error.value.code == "WEATHER_BUSY"
    finally:
        http._slots.release()
        http._slots.release()
    with pytest.raises(HTTPError):
        transport.NoRedirect().redirect_request(
            type("Request", (), {"full_url": transport.POWER_ENDPOINT})(),
            None,
            302,
            "redirect",
            {},
            "http://127.0.0.1/private",
        )

    def failing(*args):
        raise URLError("private provider details")

    monkeypatch.setattr(transport, "build_opener", failing)
    for _ in range(3):
        with pytest.raises(WeatherUnavailable) as error:
            http.get(transport.POWER_ENDPOINT, {}, 10)
        assert "private" not in error.value.message

    response_body = io.BytesIO(b"private provider body")

    def http_error(*args):
        raise HTTPError(transport.POWER_ENDPOINT, 429, "rate limit", {}, response_body)

    monkeypatch.setattr(transport, "build_opener", http_error)
    with pytest.raises(WeatherUnavailable) as error:
        http.get(transport.POWER_ENDPOINT, {}, 10)
    assert error.value.code == "WEATHER_NETWORK_FAILED" and response_body.closed
