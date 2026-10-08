"""Isolated migrated databases: local SQLite and opt-in PostgreSQL CI schemas."""

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from crop_twin.core.settings import Settings
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.main import create_app
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url

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
def client(database_url: str) -> Iterator[TestClient]:
    """Exercise the real API, SQL adapter and migrations in an isolated database."""
    with TestClient(
        create_app(Settings(environment="test", database_url=SecretStr(database_url)))
    ) as api:
        yield api
