"""Verify actual M1 data upgrade and atomic mutation/audit rollback."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from crop_twin.application.identity_service import IdentityService
from crop_twin.core.settings import Settings
from crop_twin.domain.identity.rules import IdentityConflict
from crop_twin.infrastructure.database.farm_repository import SqlFarmRepository
from crop_twin.infrastructure.database.identity_repository import SqlIdentityRepository
from crop_twin.infrastructure.database.models import PlotRecord
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.infrastructure.passwords import Argon2Passwords
from crop_twin.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]


def test_upgrade_preserves_legacy_farm_and_requires_explicit_ownership(database_url: str) -> None:
    engine = build_engine(database_url)
    plot_id, season_id, event_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    try:
        config = Config(str(ROOT / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            # The isolated fixture contains no accounts or application data.
            command.downgrade(config, "0001_farm_records")
            metadata = sa.MetaData()
            plot = sa.Table(
                "plots",
                metadata,
                sa.Column("id", sa.Uuid()),
                sa.Column("name", sa.String()),
                sa.Column("area_mu", sa.Numeric()),
                sa.Column("latitude", sa.Float()),
                sa.Column("longitude", sa.Float()),
                sa.Column("created_at", sa.DateTime(timezone=True)),
            )
            season = sa.Table(
                "seasons",
                metadata,
                sa.Column("id", sa.Uuid()),
                sa.Column("plot_id", sa.Uuid()),
                sa.Column("start_date", sa.Date()),
                sa.Column("end_date", sa.Date()),
                sa.Column("establishment_method", sa.String()),
                sa.Column("created_at", sa.DateTime(timezone=True)),
            )
            event = sa.Table(
                "management_events",
                metadata,
                sa.Column("id", sa.Uuid()),
                sa.Column("season_id", sa.Uuid()),
                sa.Column("event_type", sa.String()),
                sa.Column("occurred_on", sa.Date()),
                sa.Column("notes", sa.Text()),
                sa.Column("revision", sa.Integer()),
                sa.Column("created_at", sa.DateTime(timezone=True)),
            )
            connection.execute(
                plot.insert().values(
                    id=plot_id,
                    name="升级前农田",
                    area_mu=Decimal("15"),
                    latitude=23.1,
                    longitude=113.2,
                    created_at=now,
                )
            )
            connection.execute(
                season.insert().values(
                    id=season_id,
                    plot_id=plot_id,
                    start_date=date(2026, 3, 1),
                    establishment_method="transplanting",
                    created_at=now,
                )
            )
            connection.execute(
                event.insert().values(
                    id=event_id,
                    season_id=season_id,
                    event_type="inspection",
                    occurred_on=date(2026, 3, 5),
                    notes="原始巡田记录",
                    revision=1,
                    created_at=now,
                )
            )
            command.upgrade(config, "head")
        passwords = Argon2Passwords()
        with Session(engine) as session:
            assert session.get(PlotRecord, plot_id).organization_id is None
            session.rollback()
            with session.begin(), pytest.raises(IdentityConflict, match="旧地块"):
                IdentityService(SqlIdentityRepository(session), passwords).bootstrap(
                    "upgrade_owner", "升级管理员", "upgrade-test-passphrase", "升级测试组织"
                )
            with session.begin():
                user, count = IdentityService(SqlIdentityRepository(session), passwords).bootstrap(
                    "upgrade_owner",
                    "升级管理员",
                    "upgrade-test-passphrase",
                    "升级测试组织",
                    adopt_legacy=True,
                )
                assert count == 1
        with TestClient(
            create_app(Settings(environment="test", database_url=SecretStr(database_url)))
        ) as api:
            assert api.get(f"/api/v1/plots/{plot_id}").status_code == 401
            result = api.post(
                "/api/v1/auth/login",
                json={"username": user.username, "password": "upgrade-test-passphrase"},
            )
            assert result.status_code == 200
            assert api.get(f"/api/v1/plots/{plot_id}").json()["name"] == "升级前农田"
            assert api.get(f"/api/v1/seasons?plot_id={plot_id}").json()["items"][0]["id"] == str(
                season_id
            )
            operations = api.get(f"/api/v1/management-events?season_id={season_id}").json()
            assert operations["items"][0]["notes"] == "原始巡田记录"
            assert operations["items"][0]["id"] == str(event_id)
            assert "identity.legacy_adopted" in {
                row["action"] for row in api.get("/api/v1/audit-events").json()["items"]
            }
    finally:
        engine.dispose()


def test_audit_failure_rolls_back_the_already_flushed_plot(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    before = client.get("/api/v1/audit-events").json()["total"]

    def unavailable_audit(*args, **kwargs):
        raise OperationalError(
            "private SQL statement",
            {"credential": "never-echo-marker"},
            RuntimeError("storage test"),
        )

    monkeypatch.setattr(SqlFarmRepository, "record_audit", unavailable_audit)
    response = client.post(
        "/api/v1/plots",
        json={"name": "不能部分提交", "area_mu": "15", "latitude": 23.1, "longitude": 113.2},
    )
    assert response.status_code == 503
    assert client.get("/api/v1/plots").json()["total"] == 0
    assert client.get("/api/v1/audit-events").json()["total"] == before
    assert "never-echo-marker" not in response.text + caplog.text
    assert "private SQL" not in response.text + caplog.text
