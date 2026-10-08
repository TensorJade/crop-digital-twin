"""FastAPI application factory and local development entrypoint."""

from fastapi import FastAPI

from crop_twin import __version__
from crop_twin.api.v1.health import router as health_router
from crop_twin.core.settings import Settings


def create_app() -> FastAPI:
    """Create an API instance with validated settings and implemented routes only."""
    application = FastAPI(
        title="Crop Digital Twin API",
        version=__version__,
        description="Development scaffold. Only process liveness is implemented.",
    )
    application.state.settings = Settings()
    application.include_router(health_router)
    return application


app = create_app()
