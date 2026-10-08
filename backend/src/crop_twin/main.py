"""FastAPI application factory and local development entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from crop_twin import __version__
from crop_twin.api.v1.farm import router as farm_router
from crop_twin.api.v1.health import router as health_router
from crop_twin.core.settings import Settings
from crop_twin.domain.farm.rules import FarmConflict, FarmError, FarmNotFound
from crop_twin.infrastructure.database.session import build_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the local farm API; unauthenticated production startup is rejected."""
    configuration = settings or Settings()
    if configuration.environment == "production":
        raise RuntimeError("Account and plot authorization must be implemented before production.")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(configuration.database_url.get_secret_value())
        application.state.session_factory = sessionmaker(engine, expire_on_commit=False)
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Crop Digital Twin API",
        version=__version__,
        description="Local farm management for South China rice; simulation is pending.",
        lifespan=lifespan,
    )
    application.state.settings = configuration
    application.include_router(health_router)
    application.include_router(farm_router)

    @application.exception_handler(FarmError)
    async def farm_error_handler(request: Request, error: FarmError) -> JSONResponse:
        status = (
            404
            if isinstance(error, FarmNotFound)
            else 409
            if isinstance(error, FarmConflict)
            else 400
        )
        return JSONResponse(
            status_code=status,
            content={
                "detail": {
                    "code": error.code,
                    "message": error.message,
                }
            },
        )

    @application.exception_handler(DBAPIError)
    async def database_error_handler(request: Request, error: DBAPIError) -> JSONResponse:
        # SQL exceptions can embed parameters or connection secrets; do not log their text.
        logging.getLogger("crop_twin.database").error(
            "database operation failed: %s", type(error).__name__
        )
        conflict = isinstance(error, IntegrityError)
        return JSONResponse(
            status_code=409 if conflict else 503,
            content={
                "detail": {
                    "code": "STORAGE_CONFLICT" if conflict else "STORAGE_UNAVAILABLE",
                    "message": "记录发生冲突，请刷新后重试"
                    if conflict
                    else "数据存储暂不可用，请检查数据库初始化或连接",
                }
            },
        )

    return application


app = create_app()
