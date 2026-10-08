"""Real authentication, tenant isolation, CSRF, revocation and audit regressions."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from crop_twin.api.v1.dependencies import SESSION_COOKIE
from crop_twin.application.identity_service import token_digest
from crop_twin.core.settings import Settings
from crop_twin.domain.identity.models import User
from crop_twin.infrastructure.database.identity_models import (
    LoginLimitRecord,
    SessionRecord,
    UserRecord,
)
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session

PASSWORD = "integration-test-passphrase"


def login(api: TestClient, username: str, password: str = PASSWORD) -> dict:
    response = api.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    api.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


def member(api: TestClient, username: str, role: str = "viewer") -> dict:
    response = api.post(
        "/api/v1/users",
        json={
            "username": username,
            "display_name": "测试成员",
            "password": PASSWORD,
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def farm(api: TestClient) -> tuple[str, str, str]:
    plot = api.post(
        "/api/v1/plots",
        json={
            "name": "私有测试地块",
            "area_mu": "15",
            "latitude": 23.1,
            "longitude": 113.2,
        },
    )
    assert plot.status_code == 201
    season = api.post(
        "/api/v1/seasons",
        json={
            "plot_id": plot.json()["id"],
            "start_date": "2026-03-01",
            "establishment_method": "transplanting",
        },
    )
    assert season.status_code == 201
    event = api.post(
        "/api/v1/management-events",
        json={
            "season_id": season.json()["id"],
            "event_type": "inspection",
            "occurred_on": "2026-03-05",
        },
    )
    assert event.status_code == 201
    return plot.json()["id"], season.json()["id"], event.json()["id"]


def test_anonymous_cannot_read_or_write_farm(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/api/v1/plots").status_code == 401
    assert (
        anonymous_client.post(
            "/api/v1/plots",
            json={
                "name": "无权限",
                "area_mu": "15",
                "latitude": 23,
                "longitude": 113,
            },
        ).status_code
        == 401
    )
    assert anonymous_client.get("/api/v1/auth/me").status_code == 401
    assert anonymous_client.get("/api/v1/health").status_code == 200


def test_cookie_digest_and_public_responses_do_not_expose_credentials(
    client: TestClient,
    database_url: str,
) -> None:
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.headers["Cache-Control"] == "no-store"
    assert "password" not in me.text
    raw_token = client.cookies.get(SESSION_COOKIE)
    assert raw_token and raw_token not in me.text
    engine = build_engine(database_url)
    try:
        with Session(engine) as session:
            stored = session.scalar(select(SessionRecord))
            account = session.scalar(select(UserRecord))
            assert stored and stored.token_digest == token_digest(raw_token)
            assert account and account.password_hash.startswith("$argon2id$")
            assert PASSWORD not in account.password_hash
    finally:
        engine.dispose()
    response = client.post(
        "/api/v1/auth/login", json={"username": "test_owner", "password": PASSWORD}
    )
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/api" in cookie
    assert raw_token != client.cookies.get(SESSION_COOKIE)


@pytest.mark.parametrize("csrf", [None, "wrong-token", "non-ascii-\u00e9"])
def test_write_requires_session_bound_csrf(client: TestClient, csrf: str | None) -> None:
    client.headers.pop("X-CSRF-Token")
    headers = {"X-CSRF-Token": csrf.encode("utf-8")} if csrf is not None else {}
    response = client.post(
        "/api/v1/plots",
        json={
            "name": "拒绝写入",
            "area_mu": "15",
            "latitude": 23,
            "longitude": 113,
        },
        headers=headers,
    )
    assert response.status_code == 403
    assert client.get("/api/v1/plots").json()["total"] == 0


def test_foreign_browser_origin_cannot_login_or_write(client: TestClient) -> None:
    foreign = {"Origin": "https://foreign.example"}
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_owner",
                "password": PASSWORD,
            },
            headers=foreign,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/plots",
            json={
                "name": "拒绝来源",
                "area_mu": "15",
                "latitude": 23,
                "longitude": 113,
            },
            headers=foreign,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "username": "test_owner",
                "password": PASSWORD,
            },
            headers={"Origin": "http://127.0.0.1:5173"},
        ).status_code
        == 200
    )


def test_validation_errors_redact_password_and_unknown_secret_fields(client: TestClient) -> None:
    marker = "shortsecret"
    response = client.post(
        "/api/v1/users",
        json={
            "username": "member",
            "display_name": "成员",
            "role": "viewer",
            "password": marker,
            "unknown_secret": "must-never-echo",
        },
    )
    assert response.status_code == 422
    assert marker not in response.text and "must-never-echo" not in response.text
    assert all("input" not in error for error in response.json()["detail"])
    users = client.get("/api/v1/users").json()
    assert users["total"] == 1 and "password_hash" not in str(users)


def test_failed_login_window_survives_restart_and_has_uniform_errors(
    anonymous_client: TestClient,
    owner_user: User,
    database_url: str,
) -> None:
    results = []
    for username in [
        owner_user.username,
        "missing_user",
        owner_user.username,
        "missing_user",
        owner_user.username,
    ]:
        response = anonymous_client.post(
            "/api/v1/auth/login",
            json={
                "username": username,
                "password": "wrong-test-password",
            },
        )
        assert response.status_code == 401
        results.append(response.json())
    assert all(body == results[0] for body in results)
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as restarted:
        blocked = restarted.post(
            "/api/v1/auth/login",
            json={
                "username": owner_user.username,
                "password": PASSWORD,
            },
        )
        assert blocked.status_code == 429 and blocked.headers["Retry-After"] == "900"
    engine = build_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                update(LoginLimitRecord).values(
                    window_start=datetime.now(UTC) - timedelta(minutes=16)
                )
            )
    finally:
        engine.dispose()
    login(anonymous_client, owner_user.username)


def test_logout_revokes_the_old_cookie(client: TestClient) -> None:
    old = client.cookies.get(SESSION_COOKIE)
    assert client.post("/api/v1/auth/logout").status_code == 200
    client.cookies.set(SESSION_COOKIE, old or "", path="/api")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_expired_session_cannot_read(client: TestClient, database_url: str) -> None:
    engine = build_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                update(SessionRecord).values(
                    created_at=datetime.now(UTC) - timedelta(days=2),
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
    finally:
        engine.dispose()
    assert client.get("/api/v1/plots").status_code == 401


def test_password_change_requires_current_password_and_revokes_every_session(
    client: TestClient,
    database_url: str,
) -> None:
    new_password = "new-integration-passphrase"
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as second:
        login(second, "test_owner")
        denied = client.post(
            "/api/v1/auth/password",
            json={
                "current_password": "wrong-password",
                "new_password": new_password,
            },
        )
        assert denied.status_code == 400
        assert second.get("/api/v1/auth/me").status_code == 200
        assert (
            client.post(
                "/api/v1/auth/password",
                json={
                    "current_password": PASSWORD,
                    "new_password": new_password,
                },
            ).status_code
            == 200
        )
        assert second.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "test_owner", "password": PASSWORD}
        ).status_code
        == 401
    )
    login(client, "test_owner", new_password)


def test_reader_can_read_but_cannot_write_or_manage_users(
    client: TestClient, database_url: str
) -> None:
    member(client, "test_reader")
    plot_id, season_id, event_id = farm(client)
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as reader:
        login(reader, "test_reader")
        assert reader.get(f"/api/v1/plots/{plot_id}").status_code == 200
        assert reader.get(f"/api/v1/management-events?season_id={season_id}").json()["total"] == 1
        for path, payload in [
            ("/api/v1/plots", {"name": "越权", "area_mu": "15", "latitude": 23, "longitude": 113}),
            (f"/api/v1/seasons/{season_id}/close", {"end_date": "2026-06-30"}),
            (
                f"/api/v1/management-events/{event_id}/corrections",
                {
                    "event_type": "inspection",
                    "occurred_on": "2026-03-05",
                    "correction_reason": "越权",
                },
            ),
        ]:
            assert reader.post(path, json=payload).status_code == 403
        assert reader.get("/api/v1/users").status_code == 403
        assert reader.get("/api/v1/audit-events").status_code == 403


def test_operator_can_write_but_cannot_create_accounts(
    client: TestClient, database_url: str
) -> None:
    member(client, "test_operator", "operator")
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as operator:
        login(operator, "test_operator")
        farm(operator)
        assert (
            operator.post(
                "/api/v1/users",
                json={
                    "username": "unapproved",
                    "display_name": "不允许",
                    "password": PASSWORD,
                    "role": "viewer",
                },
            ).status_code
            == 403
        )


def test_cross_organization_ids_are_hidden_for_every_farm_relation(
    client: TestClient,
    database_url: str,
    make_owner: Callable[[str, str], User],
) -> None:
    other_user = make_owner("other_owner", "另一组织")
    assert (
        client.post(f"/api/v1/users/{other_user.id}/active", json={"is_active": False}).status_code
        == 404
    )
    plot_id, season_id, event_id = farm(client)
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as other:
        login(other, other_user.username)
        assert other.get("/api/v1/plots").json()["total"] == 0
        assert other.get("/api/v1/organization").json()["id"] == str(other_user.organization_id)
        assert all(
            user["organization_id"] == str(other_user.organization_id)
            for user in other.get("/api/v1/users").json()["items"]
        )
        for url in [
            f"/api/v1/plots/{plot_id}",
            f"/api/v1/seasons?plot_id={plot_id}",
            f"/api/v1/management-events?season_id={season_id}&include_history=true",
        ]:
            assert other.get(url).status_code == 404
        for url, payload in [
            (
                "/api/v1/seasons",
                {
                    "plot_id": plot_id,
                    "start_date": "2026-08-01",
                    "establishment_method": "direct_sowing",
                },
            ),
            (f"/api/v1/seasons/{season_id}/close", {"end_date": "2026-06-30"}),
            (
                "/api/v1/management-events",
                {"season_id": season_id, "event_type": "inspection", "occurred_on": "2026-03-05"},
            ),
            (
                f"/api/v1/management-events/{event_id}/corrections",
                {
                    "event_type": "inspection",
                    "occurred_on": "2026-03-05",
                    "correction_reason": "越权",
                },
            ),
        ]:
            assert other.post(url, json=payload).status_code == 404
        assert all(
            event["organization_id"] == str(other_user.organization_id)
            for event in other.get("/api/v1/audit-events").json()["items"]
        )


def test_owner_cannot_grant_owner_role_or_client_selected_organization(client: TestClient) -> None:
    payload = {
        "username": "member_two",
        "display_name": "成员",
        "password": PASSWORD,
        "role": "owner",
    }
    assert client.post("/api/v1/users", json=payload).status_code == 422
    payload.update(role="viewer", organization_id="00000000-0000-0000-0000-000000000000")
    assert client.post("/api/v1/users", json=payload).status_code == 422


def test_member_deactivation_revokes_sessions_and_reactivation_needs_new_login(
    client: TestClient,
    database_url: str,
    owner_user: User,
) -> None:
    account = member(client, "deactivated_member", "operator")
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as operator:
        login(operator, account["username"])
        assert (
            client.post(
                f"/api/v1/users/{account['id']}/active", json={"is_active": False}
            ).status_code
            == 200
        )
        assert operator.get("/api/v1/plots").status_code == 401
        assert (
            operator.post(
                "/api/v1/auth/login", json={"username": account["username"], "password": PASSWORD}
            ).status_code
            == 401
        )
        assert (
            client.post(
                f"/api/v1/users/{account['id']}/active", json={"is_active": True}
            ).status_code
            == 200
        )
        assert operator.get("/api/v1/plots").status_code == 401
        login(operator, account["username"])
    assert (
        client.post(f"/api/v1/users/{owner_user.id}/active", json={"is_active": False}).status_code
        == 403
    )


def test_member_and_audit_pagination_is_scoped_and_failed_writes_leave_no_audit(
    client: TestClient,
) -> None:
    first = member(client, "first_member")
    assert (
        client.post(
            "/api/v1/users",
            json={
                "username": "FIRST_MEMBER",
                "display_name": "重复",
                "password": PASSWORD,
                "role": "viewer",
            },
        ).status_code
        == 409
    )
    farm(client)
    before = client.get("/api/v1/audit-events").json()["total"]
    assert (
        client.post(
            "/api/v1/plots",
            json={
                "name": "无效面积",
                "area_mu": "0",
                "latitude": 23,
                "longitude": 113,
            },
        ).status_code
        == 422
    )
    assert client.get("/api/v1/audit-events").json()["total"] == before
    accounts = client.get("/api/v1/users?limit=1&offset=0").json()
    assert accounts["total"] == 2 and accounts["items"][0]["id"] == first["id"]
    events = client.get("/api/v1/audit-events?limit=2&offset=1").json()
    assert len(events["items"]) == 2 and events["total"] == before
    assert "password" not in str(events) and "token" not in str(events)
    assert {item["action"] for item in client.get("/api/v1/audit-events").json()["items"]} >= {
        "identity.bootstrap",
        "auth.login",
        "identity.user_created",
        "farm.plot_created",
        "farm.season_created",
        "farm.event_created",
    }


def test_distinct_accounts_cannot_concurrently_create_overlapping_seasons(
    client: TestClient,
    database_url: str,
) -> None:
    account = member(client, "concurrent_operator", "operator")
    plot = client.post(
        "/api/v1/plots",
        json={
            "name": "多人管理田",
            "area_mu": "15",
            "latitude": 23.1,
            "longitude": 113.2,
        },
    ).json()
    payload = {
        "plot_id": plot["id"],
        "start_date": "2026-03-01",
        "establishment_method": "transplanting",
    }
    gate = Barrier(2)
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as operator:
        login(operator, account["username"])

        def submit(api: TestClient) -> int:
            gate.wait(timeout=10)
            return api.post("/api/v1/seasons", json=payload).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(submit, [client, operator])) == [201, 409]
    assert client.get(f"/api/v1/seasons?plot_id={plot['id']}").json()["total"] == 1
    assert (
        sum(
            row["action"] == "farm.season_created"
            for row in client.get("/api/v1/audit-events").json()["items"]
        )
        == 1
    )
