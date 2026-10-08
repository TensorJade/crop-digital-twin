"""Real persistence and business acceptance, parametrized across database adapters."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from conftest import ROOT
from crop_twin.core.settings import Settings
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr


def plot_payload() -> dict[str, object]:
    """A clearly labeled test plot, unrelated to real farm observations."""
    return {"name": "测试地块", "area_mu": "15", "latitude": 23.1, "longitude": 113.2}


def create_plot(client: TestClient) -> str:
    response = client.post("/api/v1/plots", json=plot_payload())
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def create_season(client: TestClient, plot_id: str | None = None) -> str:
    response = client.post(
        "/api/v1/seasons",
        json={
            "plot_id": plot_id or create_plot(client),
            "start_date": "2026-03-01",
            "establishment_method": "transplanting",
            "variety_name": "测试品种",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def event_payload(season_id: str, **changes: object) -> dict[str, object]:
    return {
        "season_id": season_id,
        "event_type": "irrigation",
        "occurred_on": "2026-03-10",
        "quantity": "100",
        "unit": "m3",
        **changes,
    }


def test_plot_round_trip_and_pagination(client: TestClient) -> None:
    first = create_plot(client)
    create_plot(client)
    saved = client.get(f"/api/v1/plots/{first}")
    assert saved.status_code == 200
    assert Decimal(saved.json()["area_ha"]) == Decimal(1)
    assert saved.json()["created_at"].endswith("Z")
    page = client.get("/api/v1/plots?limit=1&offset=1").json()
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["items"][0]["id"] == first
    assert client.get("/api/v1/plots?limit=0").status_code == 422


@pytest.mark.parametrize(
    "changes",
    [{"area_mu": "0"}, {"name": "  "}, {"latitude": 91}, {"longitude": -181}, {"unexpected": True}],
)
def test_invalid_plot_does_not_persist(client: TestClient, changes: dict[str, object]) -> None:
    assert client.post("/api/v1/plots", json={**plot_payload(), **changes}).status_code == 422
    assert client.get("/api/v1/plots").json()["total"] == 0


def test_missing_parent_does_not_create_orphan(client: TestClient) -> None:
    missing = str(uuid4())
    assert client.get(f"/api/v1/plots/{missing}").status_code == 404
    assert (
        client.post(
            "/api/v1/seasons",
            json={
                "plot_id": missing,
                "start_date": "2026-03-01",
                "establishment_method": "direct_sowing",
            },
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/seasons?plot_id={missing}").status_code == 404
    assert client.post("/api/v1/management-events", json=event_payload(missing)).status_code == 404
    assert client.get(f"/api/v1/management-events?season_id={missing}").status_code == 404


def test_open_season_conflict_and_next_season(client: TestClient) -> None:
    plot_id = create_plot(client)
    season_id = create_season(client, plot_id)
    payload = {
        "plot_id": plot_id,
        "start_date": "2026-07-01",
        "establishment_method": "direct_sowing",
    }
    assert client.post("/api/v1/seasons", json=payload).status_code == 409
    assert (
        client.post(
            f"/api/v1/seasons/{season_id}/close", json={"end_date": "2026-06-30"}
        ).status_code
        == 200
    )
    assert client.post("/api/v1/seasons", json=payload).status_code == 201
    assert client.get(f"/api/v1/seasons?plot_id={plot_id}").json()["total"] == 2


def test_invalid_and_overlapping_closed_seasons(client: TestClient) -> None:
    plot_id = create_plot(client)
    payload = {
        "plot_id": plot_id,
        "start_date": "2026-03-01",
        "end_date": "2026-06-30",
        "establishment_method": "direct_sowing",
    }
    assert (
        client.post("/api/v1/seasons", json={**payload, "end_date": "2026-02-01"}).status_code
        == 400
    )
    assert client.post("/api/v1/seasons", json=payload).status_code == 201
    assert (
        client.post(
            "/api/v1/seasons", json={**payload, "start_date": "2026-06-30", "end_date": None}
        ).status_code
        == 409
    )


def test_operations_normalize_water_and_product_mass(client: TestClient) -> None:
    season_id = create_season(client)
    irrigation = client.post("/api/v1/management-events", json=event_payload(season_id)).json()
    assert Decimal(irrigation["normalized_quantity"]) == Decimal(10)
    assert irrigation["unit"] == "m3" and irrigation["normalized_unit"] == "mm"
    fertilizer = client.post(
        "/api/v1/management-events",
        json=event_payload(
            season_id,
            event_type="fertilization",
            quantity="10",
            unit="kg/mu",
            material_name="测试肥料",
        ),
    ).json()
    assert Decimal(fertilizer["quantity"]) == Decimal(10)
    assert Decimal(fertilizer["normalized_quantity"]) == Decimal(150)
    assert fertilizer["normalized_unit"] == "kg/ha"
    inspection = client.post(
        "/api/v1/management-events",
        json=event_payload(
            season_id, event_type="inspection", quantity=None, unit=None, notes="巡田测试"
        ),
    )
    assert inspection.status_code == 201
    assert inspection.json()["normalized_quantity"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"occurred_on": "2026-02-28"},
        {"unit": "kg/ha"},
        {"quantity": None},
        {"event_type": "inspection"},
        {"material_name": "肥料"},
        {"event_type": "fertilization", "unit": "kg/mu", "material_name": None},
    ],
)
def test_invalid_operation_rolls_back(client: TestClient, changes: dict[str, object]) -> None:
    season_id = create_season(client)
    assert (
        client.post(
            "/api/v1/management-events", json=event_payload(season_id, **changes)
        ).status_code
        == 400
    )
    assert client.get(f"/api/v1/management-events?season_id={season_id}").json()["total"] == 0


def test_corrections_retain_history_and_reject_stale_version(client: TestClient) -> None:
    season_id = create_season(client)
    original = client.post("/api/v1/management-events", json=event_payload(season_id)).json()
    replacement = event_payload(season_id, quantity="200", correction_reason="修正数量录入错误")
    replacement.pop("season_id")
    endpoint = f"/api/v1/management-events/{original['id']}/corrections"
    corrected = client.post(endpoint, json=replacement)
    assert corrected.status_code == 201
    assert corrected.json()["revision"] == 2
    assert corrected.json()["replaces_event_id"] == original["id"]
    assert client.post(endpoint, json=replacement).status_code == 409
    current = client.get(f"/api/v1/management-events?season_id={season_id}").json()
    history = client.get(
        f"/api/v1/management-events?season_id={season_id}&include_history=true"
    ).json()
    assert current["total"] == 1 and history["total"] == 2
    old = next(item for item in history["items"] if item["id"] == original["id"])
    assert not old["is_current"] and Decimal(old["quantity"]) == Decimal(100)
    assert (
        client.post(
            f"/api/v1/management-events/{uuid4()}/corrections", json=replacement
        ).status_code
        == 404
    )


def test_close_season_respects_current_records_and_is_idempotent(client: TestClient) -> None:
    season_id = create_season(client)
    assert (
        client.post("/api/v1/management-events", json=event_payload(season_id)).status_code == 201
    )
    close_url = f"/api/v1/seasons/{season_id}/close"
    assert client.post(close_url, json={"end_date": "2026-02-28"}).status_code == 400
    assert client.post(close_url, json={"end_date": "2026-03-09"}).status_code == 400
    assert client.post(close_url, json={"end_date": "2026-03-10"}).status_code == 200
    assert client.post(close_url, json={"end_date": "2026-03-10"}).status_code == 200
    assert client.post(close_url, json={"end_date": "2026-03-11"}).status_code == 409
    assert (
        client.post(
            "/api/v1/management-events", json=event_payload(season_id, occurred_on="2026-03-11")
        ).status_code
        == 400
    )


def test_simultaneous_seasons_serialize(client: TestClient) -> None:
    plot_id = create_plot(client)
    gate = Barrier(2)

    def submit() -> int:
        gate.wait(timeout=10)
        return client.post(
            "/api/v1/seasons",
            json={
                "plot_id": plot_id,
                "start_date": "2026-03-01",
                "establishment_method": "transplanting",
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(outcomes) == [201, 409]
    assert client.get(f"/api/v1/seasons?plot_id={plot_id}").json()["total"] == 1


def test_simultaneous_corrections_have_one_successor(client: TestClient) -> None:
    season_id = create_season(client)
    original = client.post("/api/v1/management-events", json=event_payload(season_id)).json()
    payload = event_payload(season_id, quantity="200", correction_reason="并发修正测试")
    payload.pop("season_id")
    gate = Barrier(2)

    def submit() -> int:
        gate.wait(timeout=10)
        return client.post(
            f"/api/v1/management-events/{original['id']}/corrections", json=payload
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(outcomes) == [201, 409]
    assert (
        client.get(f"/api/v1/management-events?season_id={season_id}&include_history=true").json()[
            "total"
        ]
        == 2
    )


def test_persistence_survives_app_restart(client: TestClient, database_url: str) -> None:
    plot_id = create_plot(client)
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as restarted:
        restarted.cookies.update(client.cookies)
        assert restarted.get(f"/api/v1/plots/{plot_id}").json()["name"] == "测试地块"


def test_migration_matches_models(database_url: str) -> None:
    engine = build_engine(database_url)
    try:
        with engine.begin() as connection:
            config = Config(str(ROOT / "alembic.ini"))
            config.attributes["connection"] = connection
            command.check(config)
    finally:
        engine.dispose()
