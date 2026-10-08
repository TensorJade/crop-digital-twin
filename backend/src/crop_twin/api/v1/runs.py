"""Scoped queue/query API; all scientific computation happens in a separate worker."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from crop_twin.api.v1.dependencies import DatabaseDependency
from crop_twin.api.v1.inputs import InputDependency, Limit, Offset
from crop_twin.api.v1.run_schemas import RunCreate, RunResponse, RunSummary
from crop_twin.api.v1.schemas import ErrorResponse, PageResponse
from crop_twin.application.run_service import SimulationRunService
from crop_twin.infrastructure.database.run_repository import SqlRunRepository

router = APIRouter(
    prefix="/api/v1/simulation-runs",
    tags=["simulation"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 503)},
)


def run_service(inputs: InputDependency, session: DatabaseDependency) -> SimulationRunService:
    """Use the already authorized SQL transaction and organization scope."""
    return SimulationRunService(SqlRunRepository(session, inputs.actor.organization_id), inputs)


RunDependency = Annotated[SimulationRunService, Depends(run_service, scope="function")]


@router.post("", response_model=RunSummary, status_code=202, operation_id="createSimulationRun")
def create_run(data: RunCreate, service: RunDependency) -> object:
    """Queue the chosen snapshot; same request key is idempotent."""
    return service.create(data.input_id, data.request_key)


@router.get("", response_model=PageResponse[RunSummary], operation_id="listSimulationRuns")
def list_runs(
    season_id: UUID, service: RunDependency, limit: Limit = 20, offset: Offset = 0
) -> object:
    """Page tasks/results for a visible season."""
    return service.list(season_id, limit, offset)


@router.get("/{run_id}", response_model=RunResponse, operation_id="getSimulationRun")
def get_run(run_id: UUID, service: RunDependency) -> object:
    """Read status or complete calculation without exposing private lease tokens."""
    return service.get(run_id)
