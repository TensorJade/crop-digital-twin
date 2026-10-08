"""Simulation task records; scientific results are versions, not editable farm state."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

RunStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass(frozen=True)
class SimulationRun:
    """Public scoped task; lease tokens are deliberately absent."""

    id: UUID
    organization_id: UUID
    season_id: UUID
    input_id: UUID
    request_key: UUID
    actor_user_id: UUID
    model_code: str
    engine_version: str
    input_hash: str
    status: RunStatus
    attempts: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    result_hash: str | None
    result: dict[str, Any] | None
