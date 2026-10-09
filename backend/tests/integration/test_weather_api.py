"""Scoped previews, no SQL during HTTP, and sealed imports on both supported databases."""

from copy import deepcopy
from pathlib import Path

from crop_twin.domain.simulation.weather import WeatherUnavailable
from crop_twin.infrastructure.weather.http import POWER_ENDPOINT, WeatherHttp
from crop_twin.infrastructure.weather.sources import WeatherSources
from fastapi.testclient import TestClient
from sqlalchemy import event

FIXTURES = Path(__file__).resolve().parents[3] / "tests/fixtures"


class FixtureHttp(WeatherHttp):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.hook = lambda: None

    def get(self, endpoint, parameters, limit):
        self.hook()
        self.calls.append((endpoint, parameters))
        name = "power-hourly.json" if endpoint == POWER_ENDPOINT else "weather-stations.csv"
        return (FIXTURES / name).read_bytes()


def setup(client):
    http = FixtureHttp()
    client.app.state.weather_sources = WeatherSources(http)
    plot = client.post(
        "/api/v1/plots",
        json={"name": "天气验收", "area_mu": "10", "latitude": 23.1, "longitude": 113.2},
    ).json()
    query = {"plot_id": plot["id"], "start_date": "2024-03-02", "end_date": "2024-03-03"}
    return http, plot, query


def test_preview_no_write_seal_save_and_reject_modified_derivation(client):
    http, plot, query = setup(client)
    audit_before = client.get("/api/v1/audit-events").json()["total"]
    response = client.get("/api/v1/weather/preview", params=query)
    assert response.status_code == 200, response.text
    candidate = response.json()["asset"]
    assert candidate["data"]["provider"]["raw_response"]["header"]["time_standard"] == "UTC"
    assert candidate["data"]["station_id"] is None
    assert client.get("/api/v1/audit-events").json()["total"] == audit_before
    assert (
        client.get(
            "/api/v1/input-assets", params={"kind": "weather", "plot_id": plot["id"]}
        ).json()["total"]
        == 0
    )
    candidate["data"].update(angstrom_a=0.29, angstrom_b=0.49)
    created = client.post("/api/v1/input-assets", json=candidate)
    assert created.status_code == 201, created.text
    assert len(created.json()["payload"]["days"]) == 2
    assert (
        created.json()["payload"]["provider"]["raw_hash"]
        == candidate["data"]["provider"]["raw_hash"]
    )
    changed = deepcopy(candidate)
    changed["data"]["csv_text"] = changed["data"]["csv_text"].replace("2.4", "0.0")
    rejected = client.post("/api/v1/input-assets", json=changed)
    assert rejected.status_code == 422 and "校验不一致" in rejected.text
    listing = client.get("/api/v1/weather/stations", params={"plot_id": plot["id"]})
    assert listing.status_code == 200 and len(listing.json()["stations"]) == 2
    assert all(not item["observations_connected"] for item in listing.json()["stations"])
    assert len(http.calls) == 2


def test_foreign_plot_anonymous_and_viewer_never_contact_provider(client, make_owner):
    http, plot, query = setup(client)
    other_owner = make_owner("weather_other", "其他天气组织")
    with TestClient(client.app) as other:
        assert other.get("/api/v1/weather/preview", params=query).status_code == 401
        other.post(
            "/api/v1/auth/login",
            json={"username": other_owner.username, "password": "integration-test-passphrase"},
        )
        assert other.get("/api/v1/weather/preview", params=query).status_code == 404
        assert (
            other.get("/api/v1/weather/stations", params={"plot_id": plot["id"]}).status_code == 404
        )
    client.post(
        "/api/v1/users",
        json={
            "username": "weather_reader",
            "display_name": "天气只读",
            "role": "viewer",
            "password": "integration-test-passphrase",
        },
    )
    with TestClient(client.app) as reader:
        reader.post(
            "/api/v1/auth/login",
            json={"username": "weather_reader", "password": "integration-test-passphrase"},
        )
        assert reader.get("/api/v1/weather/preview", params=query).status_code == 403
        assert (
            reader.get("/api/v1/weather/stations", params={"plot_id": plot["id"]}).status_code
            == 403
        )
    assert http.calls == []


def test_sql_is_released_before_upstream_and_failure_does_not_store_partial_data(client):
    http, plot, query = setup(client)
    engine = client.app.state.session_factory.kw["bind"]
    connections = [0]

    def checkout(*args):
        connections[0] += 1

    def checkin(*args):
        connections[0] -= 1

    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)

    def network():
        assert connections[0] == 0
        raise WeatherUnavailable("WEATHER_NETWORK_FAILED", "天气源暂不可用")

    http.hook = network
    try:
        response = client.get("/api/v1/weather/preview", params=query)
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "WEATHER_NETWORK_FAILED"
        http.hook = lambda: None
        assert (
            client.get(
                "/api/v1/input-assets", params={"kind": "weather", "plot_id": plot["id"]}
            ).json()["total"]
            == 0
        )
    finally:
        event.remove(engine, "checkout", checkout)
        event.remove(engine, "checkin", checkin)


def test_invalid_dates_and_shape_never_fetch(client):
    http, _, query = setup(client)
    assert (
        client.get(
            "/api/v1/weather/preview", params={**query, "end_date": "2025-04-01"}
        ).status_code
        == 400
    )
    assert (
        client.get("/api/v1/weather/preview", params={**query, "start_date": "invalid"}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/weather/preview", params={**query, "end_date": "2099-01-01"}
        ).status_code
        == 400
    )
    assert http.calls == []
