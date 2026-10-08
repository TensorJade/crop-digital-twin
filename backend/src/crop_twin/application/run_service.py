"""Queue a verified immutable input; no PCSE import or heavy calculation in HTTP."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from crop_engine.inputs import InputDataError, content_hash
from crop_engine.potential import MODEL_CODE, PCSE_VERSION, validate_potential_input

from crop_twin.application.input_service import SimulationInputService
from crop_twin.application.run_repository import RunRepository
from crop_twin.domain.farm.rules import FarmConflict, FarmError, FarmNotFound
from crop_twin.domain.pagination import Page
from crop_twin.domain.simulation.runs import SimulationRun


class SimulationRunService:
    """Reuse scoped inputs/farm and same-transaction audit."""

    def __init__(self, repository: RunRepository, inputs: SimulationInputService) -> None:
        self.repository, self.inputs = repository, inputs

    def create(self, input_id: UUID, request_key: UUID) -> SimulationRun:
        """Check the input and idempotency key, then record a lightweight queued task."""
        snapshot = self.inputs.get_snapshot(input_id)
        self.inputs.farm.get_season(snapshot.season_id, lock=True)
        existing = self.repository.get_by_key(request_key)
        if existing:
            if existing.input_id != input_id:
                raise FarmConflict(
                    "REQUEST_KEY_CONFLICT", "该提交标识已用于另一份输入，请刷新后重试"
                )
            return existing
        if content_hash(snapshot.payload) != snapshot.content_hash:
            raise FarmError("INPUT_INTEGRITY_FAILED", "输入内容校验失败，请联系管理员")
        try:
            validate_potential_input(snapshot.payload)
        except InputDataError as error:
            raise FarmError("POTENTIAL_INPUT_INVALID", str(error)) from None
        actor = self.inputs.actor
        run = SimulationRun(
            uuid4(),
            actor.organization_id,
            snapshot.season_id,
            input_id,
            request_key,
            actor.id,
            MODEL_CODE,
            PCSE_VERSION,
            snapshot.content_hash,
            "queued",
            0,
            datetime.now(UTC),
            None,
            None,
            None,
            None,
            None,
        )
        self.repository.add(run)
        self.inputs.farm.repository.record_audit("simulation.queued", "simulation_run", run.id)
        return run

    def get(self, run_id: UUID) -> SimulationRun:
        """Return a full result only to its organization."""
        run = self.repository.get(run_id)
        if run is None:
            raise FarmNotFound("SIMULATION_RUN_NOT_FOUND", "找不到该计算任务")
        return run

    def list(self, season_id: UUID, limit: int, offset: int) -> Page[SimulationRun]:
        """Validate the season scope before listing its tasks."""
        self.inputs.farm.get_season(season_id)
        return self.repository.list(season_id, limit, offset)
