"""Apply versioned database migrations without resetting or replacing existing records."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Load optional local configuration and upgrade the configured database to head."""
    load_dotenv(ROOT / ".env", override=False)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    print("Database migrations applied; existing records preserved.")


if __name__ == "__main__":
    main()
