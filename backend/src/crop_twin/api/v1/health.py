"""Process liveness endpoint, independent of databases and model services."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from crop_twin import __version__

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(BaseModel):
    """API process status. This is not dependency readiness."""

    status: Literal["ok"] = "ok"
    service: Literal["crop-twin-api"] = "crop-twin-api"
    version: str = __version__
    scope: Literal["process"] = "process"


@router.get("/health", response_model=HealthResponse, operation_id="getApiHealth")
def get_health() -> HealthResponse:
    """Return process liveness without asserting model or database availability."""
    return HealthResponse()
