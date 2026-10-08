"""Engine creation shared by the API, migration entrypoint and database tests."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def reserve_sqlite_writer(session: Session) -> None:
    """Serialize SQLite writes before reading account or farm state."""
    if session.get_bind().dialect.name == "sqlite":
        session.execute(text("BEGIN IMMEDIATE"))


def build_engine(database_url: str) -> Engine:
    """Create a supported local SQLite or PostgreSQL/psycopg engine without logging secrets."""
    url = make_url(database_url)
    if url.drivername == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).resolve().parent.mkdir(parents=True, exist_ok=True)
        return create_engine(
            url, connect_args={"check_same_thread": False, "timeout": 30}, pool_pre_ping=True
        )
    if url.drivername == "postgresql+psycopg":
        return create_engine(url, pool_pre_ping=True)
    raise ValueError("Use sqlite or postgresql+psycopg for CROP_TWIN_DATABASE_URL")
