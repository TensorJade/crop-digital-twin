"""Organization-scoped user access to task summaries and full result versions."""

from dataclasses import asdict
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crop_twin.domain.pagination import Page
from crop_twin.domain.simulation.runs import RunStatus, SimulationRun
from crop_twin.infrastructure.database.run_models import SimulationRunRecord


def public_run(record: SimulationRunRecord) -> SimulationRun:
    """Exclude private lease state and normalize SQLite's naive UTC timestamps."""

    def utc(value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value

    return SimulationRun(
        record.id,
        record.organization_id,
        record.season_id,
        record.input_id,
        record.request_key,
        record.actor_user_id,
        record.model_code,
        record.engine_version,
        record.input_hash,
        cast(RunStatus, record.status),
        record.attempts,
        cast(datetime, utc(record.created_at)),
        utc(record.started_at),
        utc(record.finished_at),
        record.error_code,
        record.result_hash,
        record.result,
    )


class SqlRunRepository:
    """Scope task IDs and keys at the SQL boundary."""

    def __init__(self, session: Session, organization_id: UUID) -> None:
        self.session, self.organization_id = session, organization_id

    def get(self, run_id: UUID) -> SimulationRun | None:
        """Hide foreign task IDs."""
        record = self.session.scalar(
            select(SimulationRunRecord).where(
                SimulationRunRecord.id == run_id,
                SimulationRunRecord.organization_id == self.organization_id,
            )
        )
        return public_run(record) if record else None

    def get_by_key(self, request_key: UUID) -> SimulationRun | None:
        """Read an idempotent submission within one organization."""
        record = self.session.scalar(
            select(SimulationRunRecord).where(
                SimulationRunRecord.request_key == request_key,
                SimulationRunRecord.organization_id == self.organization_id,
            )
        )
        return public_run(record) if record else None

    def add(self, run: SimulationRun) -> None:
        """Insert the task under the parent season lock in the API transaction."""
        self.session.add(
            SimulationRunRecord(**asdict(run), lease_token=None, lease_expires_at=None)
        )
        self.session.flush()

    def list(self, season_id: UUID, limit: int, offset: int) -> Page[SimulationRun]:
        """Page scoped records; the response model omits result bodies."""
        conditions = (
            SimulationRunRecord.organization_id == self.organization_id,
            SimulationRunRecord.season_id == season_id,
        )
        total = (
            self.session.scalar(
                select(func.count()).select_from(SimulationRunRecord).where(*conditions)
            )
            or 0
        )
        records = self.session.scalars(
            select(SimulationRunRecord)
            .where(*conditions)
            .order_by(SimulationRunRecord.created_at.desc(), SimulationRunRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page([public_run(record) for record in records], total, limit, offset)
