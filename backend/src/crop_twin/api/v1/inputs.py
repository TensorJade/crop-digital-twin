"""Thin scoped adapters for M3.1 imports, preflight checks and immutable snapshots."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from crop_twin.api.v1.dependencies import DatabaseDependency, PrincipalDependency
from crop_twin.api.v1.input_schemas import (
    AssetCreate,
    AssetResponse,
    AssetSummary,
    ReportResponse,
    SnapshotCreate,
    SnapshotResponse,
    SnapshotSummary,
)
from crop_twin.api.v1.schemas import ErrorResponse, PageResponse
from crop_twin.application.farm_service import FarmService
from crop_twin.application.input_service import SimulationInputService
from crop_twin.domain.identity.rules import require_writer
from crop_twin.domain.simulation.models import AssetInput, AssetKind, SnapshotInput
from crop_twin.infrastructure.database.farm_repository import SqlFarmRepository
from crop_twin.infrastructure.database.input_repository import SqlInputRepository

router = APIRouter(
    prefix="/api/v1",
    tags=["simulation-inputs"],
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 503)},
)


def input_service(
    request: Request, session: DatabaseDependency, principal: PrincipalDependency
) -> SimulationInputService:
    """Reuse the account transaction, scope and writer policy for every input operation."""
    if request.method == "POST":
        require_writer(principal.user)
    organization_id = principal.user.organization_id
    farm = FarmService(
        SqlFarmRepository(session, organization_id, principal.user.id), organization_id
    )
    return SimulationInputService(
        SqlInputRepository(session, organization_id), farm, principal.user
    )


InputDependency = Annotated[SimulationInputService, Depends(input_service, scope="function")]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.get(
    "/input-assets", response_model=PageResponse[AssetSummary], operation_id="listInputAssets"
)
def list_assets(
    kind: AssetKind,
    service: InputDependency,
    plot_id: UUID | None = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> object:
    """List metadata for the plot's soil/weather or the team's crop parameter library."""
    return service.list_assets(kind, plot_id, limit, offset)


@router.post(
    "/input-assets", response_model=AssetResponse, status_code=201, operation_id="createInputAsset"
)
def create_asset(data: AssetCreate, service: InputDependency) -> object:
    """Save an explicit typed import with provenance and same-transaction audit."""
    return service.create_asset(
        AssetInput(
            data.kind,
            data.plot_id,
            data.name,
            data.source,
            data.source_license,
            data.data.model_dump(mode="json"),
        )
    )


@router.get("/input-assets/{asset_id}", response_model=AssetResponse, operation_id="getInputAsset")
def get_asset(asset_id: UUID, service: InputDependency) -> object:
    """Return the original typed payload; foreign asset IDs are 404."""
    return service.get_asset(asset_id)


@router.post(
    "/simulation-inputs/check", response_model=ReportResponse, operation_id="checkSimulationInputs"
)
def check_inputs(data: SnapshotCreate, service: InputDependency) -> object:
    """Preview completeness; this endpoint does not execute a scientific model."""
    return service.check(SnapshotInput(**data.model_dump()))


@router.get(
    "/simulation-inputs",
    response_model=PageResponse[SnapshotSummary],
    operation_id="listSimulationInputs",
)
def list_snapshots(
    season_id: UUID, service: InputDependency, limit: Limit = 20, offset: Offset = 0
) -> object:
    """Read retained input versions for an authorized season."""
    return service.list_snapshots(season_id, limit, offset)


@router.post(
    "/simulation-inputs",
    response_model=SnapshotResponse,
    status_code=201,
    operation_id="createSimulationInput",
)
def create_snapshot(data: SnapshotCreate, service: InputDependency) -> object:
    """Freeze selected assets and current management; an incomplete snapshot is labelled."""
    return service.create_snapshot(SnapshotInput(**data.model_dump()))


@router.get(
    "/simulation-inputs/{input_id}",
    response_model=SnapshotResponse,
    operation_id="getSimulationInput",
)
def get_snapshot(input_id: UUID, service: InputDependency) -> object:
    """Retrieve a frozen version with its canonical SHA-256 for export."""
    return service.get_snapshot(input_id)
