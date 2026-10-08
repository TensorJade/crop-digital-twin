"""Start the end-to-end test API on a dedicated migrated temporary SQLite database."""

from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from crop_twin.core.settings import Settings


def main() -> None:
    """Refuse non-test configuration and migrate before serving the browser suite."""
    settings = Settings()
    if settings.environment != "test":
        raise RuntimeError("e2e_api.py requires CROP_TWIN_ENVIRONMENT=test")
    root = Path(__file__).resolve().parents[1]
    command.upgrade(Config(str(root / "alembic.ini")), "head")
    uvicorn.run("crop_twin.main:app", host="127.0.0.1", port=8019)


if __name__ == "__main__":
    main()
