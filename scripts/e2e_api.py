"""Start the end-to-end test API on a dedicated migrated temporary SQLite database."""

from pathlib import Path
from tempfile import gettempdir

import uvicorn
from alembic import command
from alembic.config import Config
from crop_twin.application.identity_service import IdentityService
from crop_twin.core.settings import Settings
from crop_twin.infrastructure.database.identity_repository import SqlIdentityRepository
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.infrastructure.passwords import Argon2Passwords
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def main() -> None:
    """Refuse non-test configuration and migrate before serving the browser suite."""
    settings = Settings()
    if settings.environment != "test":
        raise RuntimeError("e2e_api.py requires CROP_TWIN_ENVIRONMENT=test")
    url = make_url(settings.database_url.get_secret_value())
    database = Path(url.database or "").resolve()
    if (
        url.drivername != "sqlite"
        or database.parent.parent != Path(gettempdir()).resolve()
        or not database.parent.name.startswith("crop-twin-e2e-")
    ):
        raise RuntimeError(
            "Browser tests require their own crop-twin-e2e-* temporary SQLite directory"
        )
    root = Path(__file__).resolve().parents[1]
    command.upgrade(Config(str(root / "alembic.ini")), "head")
    engine = build_engine(settings.database_url.get_secret_value())
    try:
        with Session(engine) as session, session.begin():
            service = IdentityService(SqlIdentityRepository(session), Argon2Passwords())
            # These credentials exist only in the positively checked temporary test database.
            service.bootstrap("e2e_owner", "验收管理员", "e2e-only-test-passphrase", "水稻验收组织")
            service.bootstrap(
                "e2e_other", "另一组织管理员", "e2e-only-test-passphrase", "另一验收组织"
            )
    finally:
        engine.dispose()
    uvicorn.run("crop_twin.main:app", host="127.0.0.1", port=8019, proxy_headers=False)


if __name__ == "__main__":
    main()
