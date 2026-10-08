"""Run migrations using an injected connection or the configured application database."""

from alembic import context
from crop_twin.core.settings import Settings
from crop_twin.infrastructure.database.identity_models import Base
from crop_twin.infrastructure.database.session import build_engine
from sqlalchemy.engine import Connection


def run_with_connection(connection: Connection) -> None:
    """Migrate only the configured connection; no implicit schema creation."""
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Use online migrations so the configured database is checked.")
elif "connection" in context.config.attributes:
    run_with_connection(context.config.attributes["connection"])
else:
    engine = build_engine(Settings().database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            run_with_connection(connection)
    finally:
        engine.dispose()
