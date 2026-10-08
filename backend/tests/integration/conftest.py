"""Isolated migrated databases: local SQLite and opt-in PostgreSQL CI schemas."""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from crop_twin.application.identity_service import IdentityService
from crop_twin.core.settings import Settings
from crop_twin.domain.identity.models import User
from crop_twin.infrastructure.database.identity_repository import SqlIdentityRepository
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.infrastructure.passwords import Argon2Passwords
from crop_twin.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(params=["sqlite", "postgresql"])
def database_url(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[str]:
    """Migrate an isolated database; never reset a user's database or application data."""
    schema: str | None = None
    if request.param == "sqlite":
        url = f"sqlite:///{(tmp_path / 'farm.db').as_posix()}"
        admin = None
    else:
        configured_url = os.environ.get("CROP_TWIN_TEST_POSTGRES_URL")
        if not configured_url:
            pytest.skip("PostgreSQL integration requires CROP_TWIN_TEST_POSTGRES_URL (set in CI)")
        admin = build_engine(configured_url)
        schema = f"test_farm_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = (
            make_url(configured_url)
            .update_query_dict({"options": f"-csearch_path={schema}"})
            .render_as_string(hide_password=False)
        )
    engine = build_engine(url)
    try:
        configuration = Config(str(ROOT / "alembic.ini"))
        with engine.begin() as connection:
            configuration.attributes["connection"] = connection
            command.upgrade(configuration, "head")
        yield url
    finally:
        engine.dispose()
        if admin is not None and schema is not None:
            # This is only the UUID-named test schema created above, never public/application data.
            assert schema.startswith("test_farm_") and len(schema) == 42
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


@pytest.fixture
def make_owner(database_url: str) -> Iterator[Callable[[str, str], User]]:
    """Create explicit owners in an isolated test database, never the runtime database."""
    engine = build_engine(database_url)
    passwords = Argon2Passwords()

    def create(username: str, organization_name: str) -> User:
        with Session(engine) as session, session.begin():
            user, _ = IdentityService(SqlIdentityRepository(session), passwords).bootstrap(
                username, username, "integration-test-passphrase", organization_name
            )
            return user

    try:
        yield create
    finally:
        engine.dispose()


@pytest.fixture
def owner_user(make_owner: Callable[[str, str], User]) -> User:
    """The test farm administrator used by M1 regressions."""
    return make_owner("test_owner", "测试水稻组")


@pytest.fixture
def anonymous_client(database_url: str) -> Iterator[TestClient]:
    """Exercise the real API, SQL adapter and migrations in an isolated database."""
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as api:
        yield api


@pytest.fixture
def client(anonymous_client: TestClient, owner_user: User) -> TestClient:
    """M1 behavior continues behind a real login and real CSRF header."""
    response = anonymous_client.post(
        "/api/v1/auth/login",
        json={
            "username": owner_user.username,
            "password": "integration-test-passphrase",
        },
    )
    assert response.status_code == 200
    anonymous_client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return anonymous_client
