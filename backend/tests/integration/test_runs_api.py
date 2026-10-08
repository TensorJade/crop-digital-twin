"""Real migrated queue/PCSE flow, organization scope, transaction rollback and lease fencing."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from crop_engine.inputs import content_hash
from crop_engine.potential import MODEL_CODE, PCSE_VERSION, SimulationFailure
from crop_twin.infrastructure.database.farm_repository import SqlFarmRepository
from crop_twin.infrastructure.database.identity_models import UserRecord
from crop_twin.infrastructure.database.input_models import SimulationInputRecord
from crop_twin.infrastructure.database.run_models import SimulationRunRecord
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.workers import simulation as worker
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]


def prepared(client):
    fixture = json.loads((ROOT / "tests/fixtures/potential-input.json").read_text(encoding="utf-8"))
    plot = client.post(
        "/api/v1/plots",
        json={"name": "计算测试田", "area_mu": "15", "latitude": 23.1, "longitude": 113.2},
    ).json()
    season = client.post(
        "/api/v1/seasons",
        json={
            "plot_id": plot["id"],
            "start_date": "2026-03-01",
            "establishment_method": "direct_sowing",
            "variety_name": fixture["season"]["variety_name"],
        },
    ).json()
    request = {"season_id": season["id"], **fixture["period"]}
    soil = {"wilting_point": 0.1, "field_capacity": 0.3, "saturation": 0.5, "depth_cm": 100}
    weather = dict(fixture["assets"]["weather"]["payload"])
    days = weather.pop("days")
    columns = ["date", "tmin_c", "tmax_c", "rain_mm", "radiation_mj_m2", "wind_m_s", "vapor_kpa"]
    weather["csv_text"] = (
        ",".join(columns)
        + "\n"
        + "\n".join(",".join(str(day[key]) for key in columns) for day in days)
    )
    for kind, data in [
        ("soil", soil),
        ("crop", fixture["assets"]["crop"]["payload"]),
        ("weather", weather),
    ]:
        response = client.post(
            "/api/v1/input-assets",
            json={
                "kind": kind,
                "name": "计算软件验收资料",
                "source": "自有合成资料，仅测试",
                "source_license": "仅软件验收",
                "plot_id": None if kind == "crop" else plot["id"],
                "data": data,
            },
        )
        assert response.status_code == 201, response.text
        request[kind + "_asset_id"] = response.json()["id"]
    response = client.post("/api/v1/simulation-inputs", json=request)
    assert response.status_code == 201, response.text
    return response.json(), request


def queue(client, snapshot, key=None):
    response = client.post(
        "/api/v1/simulation-runs",
        json={
            "input_id": snapshot["id"],
            "request_key": str(key or uuid4()),
            "acknowledge_potential_only": True,
        },
    )
    assert response.status_code == 202, response.text
    return response.json()


def synthetic_result(payload):
    return {
        "simulation_executed": True,
        "model_code": MODEL_CODE,
        "pcse_version": PCSE_VERSION,
        "daily": [{"date": "2026-03-02", "lai": 0.224}],
        "agronomically_validated": False,
    }


def test_queue_real_pcse_idempotency_and_versioned_result(client, database_url):
    snapshot, selection = prepared(client)
    assert snapshot["report"]["simulation_available"] is True
    key = uuid4()
    first = queue(client, snapshot, key)
    before = client.get("/api/v1/audit-events").json()["total"]
    assert queue(client, snapshot, key)["id"] == first["id"]
    assert client.get("/api/v1/audit-events").json()["total"] == before
    assert first["status"] == "queued" and "result" not in first and "lease_token" not in first
    engine = build_engine(database_url)
    try:
        assert worker.process_one(engine)
        assert not worker.process_one(engine)
    finally:
        engine.dispose()
    completed = client.get("/api/v1/simulation-runs/" + first["id"]).json()
    assert completed["status"] == "succeeded" and completed["attempts"] == 1
    assert len(completed["result"]["daily"]) == 15
    assert completed["result"]["management_effects_applied"] is False
    assert completed["result"]["input_hash"] == snapshot["content_hash"]
    assert completed["result_hash"] == content_hash(completed["result"])
    assert "lease_token" not in completed and "lease_expires_at" not in completed
    assert client.get("/api/v1/simulation-inputs/" + snapshot["id"]).json() == snapshot
    second = queue(client, snapshot)
    assert second["id"] != first["id"]
    listing = client.get(
        "/api/v1/simulation-runs", params={"season_id": snapshot["season_id"], "limit": 1}
    ).json()
    assert listing["total"] == 2 and "result" not in listing["items"][0]
    newer = client.post("/api/v1/simulation-inputs", json=selection).json()
    conflict = client.post(
        "/api/v1/simulation-runs",
        json={"input_id": newer["id"], "request_key": str(key), "acknowledge_potential_only": True},
    )
    assert conflict.status_code == 409


def test_invalid_input_acknowledgment_and_missing_task_are_rejected(client):
    snapshot, selection = prepared(client)
    body = {
        "input_id": snapshot["id"],
        "request_key": str(uuid4()),
        "acknowledge_potential_only": False,
    }
    assert client.post("/api/v1/simulation-runs", json=body).status_code == 422
    body["acknowledge_potential_only"] = True
    body["organization_id"] = str(uuid4())
    assert client.post("/api/v1/simulation-runs", json=body).status_code == 422
    body.pop("organization_id")
    body["input_id"] = str(uuid4())
    assert client.post("/api/v1/simulation-runs", json=body).status_code == 404
    assert client.get("/api/v1/simulation-runs/" + str(uuid4())).status_code == 404
    assert (
        client.get("/api/v1/simulation-runs", params={"season_id": str(uuid4())}).status_code == 404
    )
    selection["cutoff_date"] = "2026-03-17"
    incomplete = client.post("/api/v1/simulation-inputs", json=selection).json()
    body["input_id"] = incomplete["id"]
    assert client.post("/api/v1/simulation-runs", json=body).status_code == 400
    assert (
        client.get("/api/v1/simulation-runs", params={"season_id": snapshot["season_id"]}).json()[
            "total"
        ]
        == 0
    )


def test_scope_and_readonly_user(client, make_owner):
    snapshot, _ = prepared(client)
    run = queue(client, snapshot)
    foreign = make_owner("other_run_owner", "其他计算组织")
    with TestClient(client.app) as other:
        logged = other.post(
            "/api/v1/auth/login",
            json={"username": foreign.username, "password": "integration-test-passphrase"},
        ).json()
        other.headers["X-CSRF-Token"] = logged["csrf_token"]
        assert other.get("/api/v1/simulation-runs/" + run["id"]).status_code == 404
        assert (
            other.get(
                "/api/v1/simulation-runs", params={"season_id": snapshot["season_id"]}
            ).status_code
            == 404
        )
        assert (
            other.post(
                "/api/v1/simulation-runs",
                json={
                    "input_id": snapshot["id"],
                    "request_key": str(uuid4()),
                    "acknowledge_potential_only": True,
                },
            ).status_code
            == 404
        )
    assert (
        client.post(
            "/api/v1/users",
            json={
                "username": "run_reader",
                "display_name": "计算只读",
                "role": "viewer",
                "password": "integration-test-passphrase",
            },
        ).status_code
        == 201
    )
    with TestClient(client.app) as reader:
        login = reader.post(
            "/api/v1/auth/login",
            json={"username": "run_reader", "password": "integration-test-passphrase"},
        ).json()
        reader.headers["X-CSRF-Token"] = login["csrf_token"]
        assert reader.get("/api/v1/simulation-runs/" + run["id"]).status_code == 200
        assert (
            reader.post(
                "/api/v1/simulation-runs",
                json={
                    "input_id": snapshot["id"],
                    "request_key": str(uuid4()),
                    "acknowledge_potential_only": True,
                },
            ).status_code
            == 403
        )


@pytest.mark.parametrize(
    "code", ["ENGINE_TIMEOUT", "ENGINE_FAILED", "ENGINE_OUTPUT_INVALID", "RESULT_TOO_LARGE"]
)
def test_safe_worker_failure(client, database_url, code):
    snapshot, _ = prepared(client)
    run = queue(client, snapshot)

    def rejected(payload):
        if code == "ENGINE_FAILED":
            raise ValueError("private-value")
        if code == "ENGINE_OUTPUT_INVALID":
            return {}
        if code == "RESULT_TOO_LARGE":
            return {**synthetic_result(payload), "extra": "a" * 524289}
        raise SimulationFailure(code)

    engine = build_engine(database_url)
    try:
        assert worker.process_one(engine, rejected)
    finally:
        engine.dispose()
    response = client.get("/api/v1/simulation-runs/" + run["id"])
    assert response.json()["error_code"] == code
    assert response.json()["status"] == "failed" and response.json()["result"] is None
    assert "private-value" not in response.text


def expire(engine, run_id):
    with Session(engine) as session, session.begin():
        record = session.get(SimulationRunRecord, run_id)
        record.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)


def test_expired_lease_fences_old_worker_and_exhausts_retries(client, database_url):
    snapshot, _ = prepared(client)
    run = queue(client, snapshot)
    engine = build_engine(database_url)
    from uuid import UUID

    run_id = UUID(run["id"])
    try:
        first = worker.claim_next(engine, datetime.now(UTC))
        assert first and worker.claim_next(engine, datetime.now(UTC)) is None
        expire(engine, run_id)
        second = worker.claim_next(engine, datetime.now(UTC))
        assert second and second.token != first.token
        assert (
            worker.finish(engine, first, synthetic_result(first.payload), None, datetime.now(UTC))
            is False
        )
        expire(engine, run_id)
        third = worker.claim_next(engine, datetime.now(UTC))
        assert third
        expire(engine, run_id)
        assert worker.process_one(
            engine, lambda _: pytest.fail("Exhausted task must not calculate")
        )
    finally:
        engine.dispose()
    result = client.get("/api/v1/simulation-runs/" + run["id"]).json()
    assert (
        result["status"] == "failed"
        and result["attempts"] == 3
        and result["error_code"] == "LEASE_RETRIES_EXHAUSTED"
    )


@pytest.mark.parametrize("cause", ["actor", "input", "engine"])
def test_worker_rechecks_actor_integrity_and_version(client, database_url, cause):
    snapshot, _ = prepared(client)
    run = queue(client, snapshot)
    engine = build_engine(database_url)
    from uuid import UUID

    try:
        with Session(engine) as session, session.begin():
            if cause == "actor":
                session.get(UserRecord, UUID(run["actor_user_id"])).is_active = False
            elif cause == "input":
                record = session.get(SimulationInputRecord, UUID(snapshot["id"]))
                record.payload = {**record.payload, "changed": True}
            else:
                session.get(SimulationRunRecord, UUID(run["id"])).engine_version = "unknown"
        assert worker.process_one(engine, lambda _: pytest.fail("Invalid task must not calculate"))
        with Session(engine) as session:
            record = session.get(SimulationRunRecord, UUID(run["id"]))
            assert record.status == "failed"
            assert (
                record.error_code
                == {
                    "actor": "ACTOR_UNAVAILABLE",
                    "input": "INPUT_INTEGRITY_FAILED",
                    "engine": "ENGINE_VERSION_UNSUPPORTED",
                }[cause]
            )
    finally:
        engine.dispose()


def test_api_audit_failure_rolls_back_queue_and_two_workers_claim_once(
    client, database_url, monkeypatch
):
    snapshot, _ = prepared(client)

    def failed(*args, **kwargs):
        raise OperationalError("private", {}, RuntimeError("audit"))

    with monkeypatch.context() as context:
        context.setattr(SqlFarmRepository, "record_audit", failed)
        response = client.post(
            "/api/v1/simulation-runs",
            json={
                "input_id": snapshot["id"],
                "request_key": str(uuid4()),
                "acknowledge_potential_only": True,
            },
        )
        assert response.status_code == 503
    assert (
        client.get("/api/v1/simulation-runs", params={"season_id": snapshot["season_id"]}).json()[
            "total"
        ]
        == 0
    )
    queue(client, snapshot)
    engine = build_engine(database_url)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(lambda _: worker.process_one(engine, synthetic_result), range(2))
            )
        assert sorted(results) == [False, True]
    finally:
        engine.dispose()


def test_worker_completion_audit_failure_leaves_recoverable_lease(
    client, database_url, monkeypatch
):
    snapshot, _ = prepared(client)
    run = queue(client, snapshot)
    from uuid import UUID

    engine = build_engine(database_url)
    original = worker.audit

    def failed(session, record, action, now):
        if action == "simulation.succeeded":
            raise OperationalError("private", {}, RuntimeError("audit"))
        original(session, record, action, now)

    try:
        with monkeypatch.context() as context:
            context.setattr(worker, "audit", failed)
            with pytest.raises(OperationalError):
                worker.process_one(engine, synthetic_result)
        pending = client.get("/api/v1/simulation-runs/" + run["id"]).json()
        assert pending["status"] == "running" and pending["result"] is None
        expire(engine, UUID(run["id"]))
        assert worker.process_one(engine, synthetic_result)
    finally:
        engine.dispose()
    done = client.get("/api/v1/simulation-runs/" + run["id"]).json()
    assert done["status"] == "succeeded" and done["attempts"] == 2


@pytest.mark.parametrize(
    "a,b,status", [(None, 0.49, 422), (0.29, None, 422), (0.1, 0.3, 422), (0.29, 0.49, 201)]
)
def test_weather_coefficients_are_explicit_pairs_with_pcse_bounds(client, a, b, status):
    snapshot, _ = prepared(client)
    original = snapshot["payload"]["assets"]["weather"]
    data = {key: value for key, value in original["payload"].items() if key != "days"}
    data.update(angstrom_a=a, angstrom_b=b)
    response = client.post(
        "/api/v1/input-assets",
        json={
            "kind": "weather",
            "plot_id": original["plot_id"],
            "name": "系数检查",
            "source": "测试合成天气",
            "source_license": "仅用于软件验收",
            "data": data,
        },
    )
    assert response.status_code == status
