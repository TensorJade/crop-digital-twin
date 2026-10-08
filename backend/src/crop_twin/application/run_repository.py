"""Only the persistence operations required by user-facing simulation use cases."""

from typing import Protocol
from uuid import UUID

from crop_twin.domain.pagination import Page
from crop_twin.domain.simulation.runs import SimulationRun


class RunRepository(Protocol):
    """Every read/write is scoped to the authenticated organization."""

    def get(self, run_id: UUID) -> SimulationRun | None: ...
    def get_by_key(self, request_key: UUID) -> SimulationRun | None: ...
    def add(self, run: SimulationRun) -> None: ...
    def list(self, season_id: UUID, limit: int, offset: int) -> Page[SimulationRun]: ...
