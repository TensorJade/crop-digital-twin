"""Task contracts expose status and immutable results, never private worker leases."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from crop_twin.api.v1.input_schemas import InputModel
from crop_twin.api.v1.schemas import OutputModel
from crop_twin.domain.simulation.runs import RunStatus


class RunCreate(InputModel):
    """User explicitly chooses the water/nutrient-unlimited potential baseline."""

    input_id: UUID
    request_key: UUID
    acknowledge_potential_only: Literal[True]


class RunSummary(OutputModel):
    """A small scoped processing summary for polling and pagination."""

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


class RunResponse(RunSummary):
    """Full calculated result; failure codes contain no private engine messages."""

    result: dict[str, Any] | None
