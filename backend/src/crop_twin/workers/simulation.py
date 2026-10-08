"""Persistent task orchestration; transactions never span scientific computation."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from crop_engine.inputs import canonical_json, content_hash
from crop_engine.potential import MODEL_CODE, PCSE_VERSION, SimulationFailure, run_isolated
from crop_twin import __version__
from crop_twin.infrastructure.database.identity_models import AuditRecord, UserRecord
from crop_twin.infrastructure.database.input_models import SimulationInputRecord
from crop_twin.infrastructure.database.run_models import SimulationRunRecord
from crop_twin.infrastructure.database.session import reserve_sqlite_writer
from sqlalchemy import Engine, and_, or_, select
from sqlalchemy.orm import Session

LOGGER = logging.getLogger(__name__)
LEASE_SECONDS = 120


@dataclass(frozen=True)
class Claim:
    """Private fenced lease; it never enters an HTTP response or log."""

    run_id: UUID
    token: UUID
    payload: dict[str, Any]
    input_hash: str
    input_id: UUID
    failure: str | None


def audit(session: Session, record: SimulationRunRecord, action: str, now: datetime) -> None:
    """Append metadata with the initiating user, in the task state transaction."""
    session.add(
        AuditRecord(
            id=uuid4(),
            organization_id=record.organization_id,
            actor_user_id=record.actor_user_id,
            action=action,
            entity_type="simulation_run",
            entity_id=record.id,
            created_at=now,
        )
    )


def claim_next(engine: Engine, now: datetime) -> Claim | None:
    """Atomically claim queued/expired work; concurrent PostgreSQL workers skip locked rows."""
    with Session(engine) as session, session.begin():
        reserve_sqlite_writer(session)
        record = session.scalar(
            select(SimulationRunRecord)
            .where(
                or_(
                    SimulationRunRecord.status == "queued",
                    and_(
                        SimulationRunRecord.status == "running",
                        SimulationRunRecord.lease_expires_at <= now,
                    ),
                )
            )
            .order_by(SimulationRunRecord.created_at, SimulationRunRecord.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if record is None:
            return None
        failure = "LEASE_RETRIES_EXHAUSTED" if record.attempts >= 3 else None
        record.attempts = min(record.attempts + 1, 3)
        record.status, record.started_at = "running", now
        record.lease_token, record.lease_expires_at = (
            uuid4(),
            now + timedelta(seconds=LEASE_SECONDS),
        )
        actor = session.scalar(
            select(UserRecord).where(
                UserRecord.id == record.actor_user_id,
                UserRecord.organization_id == record.organization_id,
                UserRecord.is_active.is_(True),
                UserRecord.role.in_(("owner", "operator")),
            )
        )
        if actor is None:
            failure = "ACTOR_UNAVAILABLE"
        snapshot = session.scalar(
            select(SimulationInputRecord).where(
                SimulationInputRecord.id == record.input_id,
                SimulationInputRecord.organization_id == record.organization_id,
                SimulationInputRecord.season_id == record.season_id,
            )
        )
        payload = snapshot.payload if snapshot else {}
        if (
            snapshot is None
            or snapshot.content_hash != record.input_hash
            or content_hash(payload) != record.input_hash
        ):
            failure = "INPUT_INTEGRITY_FAILED"
        if record.model_code != MODEL_CODE or record.engine_version != PCSE_VERSION:
            failure = "ENGINE_VERSION_UNSUPPORTED"
        audit(session, record, "simulation.started", now)
        return Claim(
            record.id, record.lease_token, payload, record.input_hash, record.input_id, failure
        )


def finish(
    engine: Engine,
    claim: Claim,
    result: dict[str, Any] | None,
    error_code: str | None,
    now: datetime,
) -> bool:
    """Only the current unexpired token can persist a terminal result and audit."""
    with Session(engine) as session, session.begin():
        reserve_sqlite_writer(session)
        record = session.scalar(
            select(SimulationRunRecord)
            .where(
                SimulationRunRecord.id == claim.run_id,
                SimulationRunRecord.status == "running",
                SimulationRunRecord.lease_token == claim.token,
                SimulationRunRecord.lease_expires_at > now,
            )
            .with_for_update()
        )
        if record is None:
            return False
        record.status = "failed" if error_code else "succeeded"
        record.result, record.result_hash, record.error_code = (
            result,
            content_hash(result) if result else None,
            error_code,
        )
        record.finished_at = now
        record.lease_token, record.lease_expires_at = None, None
        audit(session, record, "simulation." + record.status, now)
        return True


def process_one(
    engine: Engine, runner: Callable[[dict[str, Any]], dict[str, Any]] = run_isolated
) -> bool:
    """Process one job outside the DB transaction; safely persist failure categories."""
    claim = claim_next(engine, datetime.now(UTC))
    if claim is None:
        return False
    result, error = None, claim.failure
    if error is None:
        try:
            calculated = runner(claim.payload)
            if (
                calculated.get("simulation_executed") is not True
                or calculated.get("model_code") != MODEL_CODE
                or calculated.get("pcse_version") != PCSE_VERSION
            ):
                raise SimulationFailure("ENGINE_OUTPUT_INVALID")
            result = {
                **calculated,
                "run_id": str(claim.run_id),
                "input_id": str(claim.input_id),
                "input_hash": claim.input_hash,
                "software_version": __version__,
            }
            if len(canonical_json(result).encode("utf-8")) > 524288:
                raise SimulationFailure("RESULT_TOO_LARGE")
        except SimulationFailure as failure:
            error = failure.code
            result = None
        except Exception:
            error, result = "ENGINE_FAILED", None
    persisted = finish(engine, claim, result, error, datetime.now(UTC))
    LOGGER.info(
        "simulation run=%s persisted=%s outcome=%s", claim.run_id, persisted, error or "succeeded"
    )
    return True
