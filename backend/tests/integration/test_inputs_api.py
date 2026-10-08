"""Real typed imports, scoped preflight, frozen history and SQL/audit transactions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from uuid import uuid4

import pytest
from crop_engine.inputs import content_hash
from crop_twin.infrastructure.database.farm_repository import SqlFarmRepository
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

HEADER = "date,tmin_c,tmax_c,rain_mm,radiation_mj_m2,wind_m_s,vapor_kpa"


def farm(client: TestClient, *, establishment_method="direct_sowing", variety="输入测试品种"):
    plot = client.post(
        "/api/v1/plots",
        json={"name": "输入测试田", "area_mu": "15", "latitude": 23.1, "longitude": 113.2},
    ).json()
    season = client.post(
        "/api/v1/seasons",
        json={
            "plot_id": plot["id"],
            "start_date": "2026-03-01",
            "establishment_method": establishment_method,
            "variety_name": variety,
        },
    ).json()
    return plot, season


def asset_body(kind: str, plot_id: str):
    body = {
        "kind": kind,
        "name": kind + "测试资料",
        "source": "隔离验收的合成资料",
        "source_license": "测试数据，仅供软件检查",
    }
    if kind == "soil":
        body.update(
            plot_id=plot_id,
            data={"wilting_point": 0.1, "field_capacity": 0.3, "saturation": 0.5, "depth_cm": 100},
        )
    elif kind == "crop":
        body["data"] = {
            "variety_name": "输入测试品种",
            "applicable_region": "软件测试",
            "parameters": {"TSUM1": 800},
        }
    else:
        body.update(
            plot_id=plot_id,
            data={
                "source_kind": "station",
                "station_id": "TEST-ONLY",
                "latitude": 23.1,
                "longitude": 113.2,
                "elevation_m": 10,
                "time_basis": "Asia/Shanghai",
                "csv_text": HEADER + "\n2026-03-02,20,30,10,15,2,1.5",
            },
        )
    return body


def inputs(client: TestClient, plot: dict, season: dict):
    body = {"season_id": season["id"], "emergence_date": "2026-03-02", "cutoff_date": "2026-03-03"}
    for kind in ("soil", "crop", "weather"):
        response = client.post("/api/v1/input-assets", json=asset_body(kind, plot["id"]))
        assert response.status_code == 201, response.text
        body[kind + "_asset_id"] = response.json()["id"]
    return body


def test_import_check_freeze_and_correction_preserve_prior_input(client: TestClient):
    plot, season = farm(client)
    request = inputs(client, plot, season)
    event = client.post(
        "/api/v1/management-events",
        json={
            "season_id": season["id"],
            "event_type": "irrigation",
            "occurred_on": "2026-03-02",
            "quantity": "150",
            "unit": "m3",
        },
    ).json()
    before = client.get("/api/v1/audit-events").json()["total"]
    checked = client.post("/api/v1/simulation-inputs/check", json=request)
    assert checked.status_code == 200
    assert checked.json()["missing_weather_days"] == 1
    assert checked.json()["simulation_available"] is False
    assert client.get("/api/v1/audit-events").json()["total"] == before
    first_response = client.post("/api/v1/simulation-inputs", json=request)
    assert first_response.status_code == 201, first_response.text
    first = first_response.json()
    assert first["content_hash"] == content_hash(first["payload"])
    assert first["payload"]["pcse_fields"]["weather"][0]["RAIN"] == 1
    assert first["payload"]["assets"]["weather"]["payload"]["days"][0]["rain_mm"] == 10
    assert first["payload"]["management_events"][0]["id"] == event["id"]
    assert first["payload"]["simulation_executed"] is False
    corrected = client.post(
        f"/api/v1/management-events/{event['id']}/corrections",
        json={
            "event_type": "irrigation",
            "occurred_on": "2026-03-02",
            "quantity": "300",
            "unit": "m3",
            "correction_reason": "软件验收修正",
        },
    ).json()
    second = client.post("/api/v1/simulation-inputs", json=request).json()
    assert second["version"] == 2
    assert second["payload"]["management_events"][0]["id"] == corrected["id"]
    assert client.get(f"/api/v1/simulation-inputs/{first['id']}").json() == first
    listing = client.get(f"/api/v1/simulation-inputs?season_id={season['id']}&limit=1").json()
    assert listing["total"] == 2 and "payload" not in listing["items"][0]
    assert listing["items"][0]["version"] == 2
    assert "inputs.snapshot_created" in {
        item["action"] for item in client.get("/api/v1/audit-events").json()["items"]
    }


@pytest.mark.parametrize(
    "elevation,blocked", [(-301, True), (-300, False), (6000, False), (6001, True)]
)
def test_weather_site_elevation_is_preserved_and_checked(
    client: TestClient, elevation: float, blocked: bool
):
    plot, season = farm(client)
    request = inputs(client, plot, season)
    weather = asset_body("weather", plot["id"])
    weather["data"]["elevation_m"] = elevation
    imported = client.post("/api/v1/input-assets", json=weather)
    assert imported.status_code == 201
    assert imported.json()["payload"]["elevation_m"] == elevation
    request["weather_asset_id"] = imported.json()["id"]
    checked = client.post("/api/v1/simulation-inputs/check", json=request)
    assert checked.status_code == 200
    codes = {issue["code"] for issue in checked.json()["blocking_issues"]}
    assert ("PCSE_ELEVATION_RANGE" in codes) is blocked


@pytest.mark.parametrize("kind", ["soil", "crop", "weather"])
def test_metadata_pagination_details_append_and_hash(client: TestClient, kind: str):
    plot, _ = farm(client)
    body = asset_body(kind, plot["id"])
    if kind == "weather":
        body["data"]["csv_text"] = (
            "\ufeff" + body["data"]["csv_text"].replace("\n", "\r\n") + "\r\n\r\n"
        )
    first = client.post("/api/v1/input-assets", json=body).json()
    if kind == "weather":
        assert first["payload"]["csv_text"] == body["data"]["csv_text"]
    second = client.post("/api/v1/input-assets", json=body).json()
    assert first["id"] != second["id"]
    assert first["content_hash"] == second["content_hash"] == content_hash(first["payload"])
    plot_query = "" if kind == "crop" else "&plot_id=" + plot["id"]
    page = client.get(f"/api/v1/input-assets?kind={kind}{plot_query}&limit=1&offset=1").json()
    assert page["total"] == 2 and page["items"][0]["id"] == first["id"]
    assert "payload" not in page["items"][0]
    assert client.get(f"/api/v1/input-assets/{first['id']}").json() == first


def test_soil_parameter_and_weather_errors_do_not_persist_or_audit(client: TestClient):
    plot, _ = farm(client)
    before = client.get("/api/v1/audit-events").json()["total"]
    soil = asset_body("soil", plot["id"])
    soil["data"]["field_capacity"] = 0.05
    assert client.post("/api/v1/input-assets", json=soil).status_code == 422
    crop = asset_body("crop", plot["id"])
    crop["data"]["parameters"] = {"AMAXTB": [0, 1, 0, 2]}
    assert client.post("/api/v1/input-assets", json=crop).status_code == 422
    crop["data"]["parameters"] = {"TSUM1": True}
    assert client.post("/api/v1/input-assets", json=crop).status_code == 422
    weather = asset_body("weather", plot["id"])
    weather["data"]["csv_text"] += "\n2026-03-02,20,30,10,15,2,1.5"
    assert client.post("/api/v1/input-assets", json=weather).status_code == 400
    weather["data"]["wind_height_m"] = 10
    assert client.post("/api/v1/input-assets", json=weather).status_code == 422
    weather["data"].pop("wind_height_m")
    weather["data"].pop("station_id")
    assert client.post("/api/v1/input-assets", json=weather).status_code == 422
    soil = asset_body("soil", plot["id"])
    soil["organization_id"] = str(uuid4())
    assert client.post("/api/v1/input-assets", json=soil).status_code == 422
    assert client.get("/api/v1/audit-events").json()["total"] == before
    assert client.get(f"/api/v1/input-assets?kind=soil&plot_id={plot['id']}").json()["total"] == 0


def test_foreign_organization_and_other_plot_assets_are_not_visible(client: TestClient, make_owner):
    plot, season = farm(client)
    body = inputs(client, plot, season)
    frozen = client.post("/api/v1/simulation-inputs", json=body).json()
    other_plot, _ = farm(client)
    wrong = client.post("/api/v1/input-assets", json=asset_body("soil", other_plot["id"])).json()
    assert (
        client.post(
            "/api/v1/simulation-inputs", json={**body, "soil_asset_id": wrong["id"]}
        ).status_code
        == 404
    )
    other = make_owner("input_other", "另一输入组织")
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": other.username, "password": "integration-test-passphrase"},
        ).status_code
        == 200
    )
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/me").json()["csrf_token"]
    assert client.get(f"/api/v1/input-assets/{body['crop_asset_id']}").status_code == 404
    assert client.get(f"/api/v1/simulation-inputs/{frozen['id']}").status_code == 404
    assert client.get(f"/api/v1/input-assets?kind=soil&plot_id={plot['id']}").status_code == 404
    assert client.get(f"/api/v1/simulation-inputs?season_id={season['id']}").status_code == 404
    assert client.post("/api/v1/simulation-inputs/check", json=body).status_code == 404
    assert client.get("/api/v1/input-assets?kind=crop").json()["total"] == 0


def test_reader_can_read_and_export_but_not_create_assets_or_snapshots(client: TestClient):
    plot, season = farm(client)
    body = inputs(client, plot, season)
    frozen = client.post("/api/v1/simulation-inputs", json=body).json()
    assert (
        client.post(
            "/api/v1/users",
            json={
                "username": "input_reader",
                "display_name": "只读输入成员",
                "password": "test-input-passphrase",
                "role": "viewer",
            },
        ).status_code
        == 201
    )
    result = client.post(
        "/api/v1/auth/login", json={"username": "input_reader", "password": "test-input-passphrase"}
    )
    client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
    assert client.get(f"/api/v1/simulation-inputs/{frozen['id']}").status_code == 200
    assert client.get("/api/v1/input-assets?kind=crop").status_code == 200
    assert (
        client.post("/api/v1/input-assets", json=asset_body("crop", plot["id"])).status_code == 403
    )
    assert client.post("/api/v1/simulation-inputs", json=body).status_code == 403
    assert client.post("/api/v1/simulation-inputs/check", json=body).status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"emergence_date": "2026-02-01"},
        {"cutoff_date": "2026-02-28"},
        {"cutoff_date": (date.today() + timedelta(days=1)).isoformat()},
        {"cutoff_date": "2025-02-01"},
        {"emergence_date": "2024-01-01"},
    ],
)
def test_snapshot_date_boundaries(client: TestClient, changes: dict):
    plot, season = farm(client)
    body = inputs(client, plot, season)
    assert client.post("/api/v1/simulation-inputs", json={**body, **changes}).status_code == 400


def test_transplant_semantics_variety_grid_time_and_location_are_explicit(client: TestClient):
    plot, season = farm(client, establishment_method="transplanting", variety="另一个测试品种")
    body = inputs(client, plot, season)
    weather = asset_body("weather", plot["id"])
    weather["data"].update(source_kind="gridded", station_id=None, latitude=24, time_basis="UTC")
    body["weather_asset_id"] = client.post("/api/v1/input-assets", json=weather).json()["id"]
    assert client.post("/api/v1/simulation-inputs/check", json=body).status_code == 400
    body["emergence_date"] = "2026-02-20"
    report = client.post("/api/v1/simulation-inputs/check", json=body).json()
    assert {"TRANSPLANT_ADAPTER_PENDING", "VARIETY_MISMATCH"} <= {
        item["code"] for item in report["blocking_issues"]
    }
    assert {"GRIDDED_WEATHER", "WEATHER_DAY_BASIS", "WEATHER_LOCATION"} <= {
        item["code"] for item in report["warnings"]
    }


def test_input_audit_failure_rolls_back_asset_and_snapshot(client: TestClient, monkeypatch):
    plot, season = farm(client)
    body = inputs(client, plot, season)
    before = client.get("/api/v1/input-assets?kind=crop").json()["total"]

    def failed_audit(*args, **kwargs):
        raise OperationalError("private-input-SQL", {}, RuntimeError("audit unavailable"))

    monkeypatch.setattr(SqlFarmRepository, "record_audit", failed_audit)
    assert (
        client.post("/api/v1/input-assets", json=asset_body("crop", plot["id"])).status_code == 503
    )
    assert client.post("/api/v1/simulation-inputs", json=body).status_code == 503
    assert client.get("/api/v1/input-assets?kind=crop").json()["total"] == before
    assert client.get(f"/api/v1/simulation-inputs?season_id={season['id']}").json()["total"] == 0


def test_concurrent_snapshots_receive_distinct_monotonic_versions(client: TestClient):
    plot, season = farm(client)
    body = inputs(client, plot, season)
    created = client.post(
        "/api/v1/users",
        json={
            "username": "input_operator",
            "display_name": "并发成员",
            "role": "operator",
            "password": "integration-test-passphrase",
        },
    )
    assert created.status_code == 201
    # Different users avoid serialization by the identity user lock, exercising the season lock.
    with TestClient(client.app) as operator:
        login = operator.post(
            "/api/v1/auth/login",
            json={"username": "input_operator", "password": "integration-test-passphrase"},
        )
        assert login.status_code == 200
        operator.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    lambda caller: caller.post("/api/v1/simulation-inputs", json=body),
                    (client, operator),
                )
            )
    assert [response.status_code for response in responses] == [201, 201]
    assert {response.json()["version"] for response in responses} == {1, 2}


def test_list_context_and_missing_id_fail_safely(client: TestClient):
    assert client.get("/api/v1/input-assets?kind=soil").status_code == 400
    assert client.get("/api/v1/input-assets?kind=crop&plot_id=" + str(uuid4())).status_code == 400
    assert client.get("/api/v1/input-assets?kind=crop&limit=201").status_code == 422
    assert client.get("/api/v1/input-assets/" + str(uuid4())).status_code == 404
    assert client.get("/api/v1/simulation-inputs/" + str(uuid4())).status_code == 404
