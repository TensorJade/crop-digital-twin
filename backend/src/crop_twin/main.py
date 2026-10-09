"""FastAPI application factory and local development entrypoint."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from crop_twin import __version__
from crop_twin.api.v1.farm import router as farm_router
from crop_twin.api.v1.health import router as health_router
from crop_twin.api.v1.identity import router as identity_router
from crop_twin.api.v1.inputs import router as inputs_router
from crop_twin.api.v1.runs import router as runs_router
from crop_twin.api.v1.weather import router as weather_router
from crop_twin.core.settings import Settings
from crop_twin.domain.farm.rules import FarmConflict, FarmError, FarmNotFound
from crop_twin.domain.identity.rules import (
    Forbidden,
    IdentityConflict,
    IdentityError,
    IdentityNotFound,
    LoginLimited,
    Unauthorized,
)
from crop_twin.domain.simulation.weather import WeatherUnavailable
from crop_twin.infrastructure.database.session import build_engine
from crop_twin.infrastructure.passwords import Argon2Passwords
from crop_twin.infrastructure.weather.sources import WeatherSources


def create_app(
    settings: Settings | None = None, *, weather_sources: WeatherSources | None = None
) -> FastAPI:
    """Create the authenticated development API; production awaits the release gate."""
    configuration = settings or Settings()
    if configuration.environment == "production":
        raise RuntimeError("Production release authorization requires the M7 deployment gate.")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(configuration.database_url.get_secret_value())
        application.state.session_factory = sessionmaker(engine, expire_on_commit=False)
        try:
            application.state.passwords = Argon2Passwords()
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Crop Digital Twin API",
        version=__version__,
        description=(
            "South China rice workspace with isolated WOFOST72 potential growth; "
            "local agronomic validation remains required."
        ),
        lifespan=lifespan,
    )
    application.state.settings = configuration
    application.state.weather_sources = weather_sources or WeatherSources()
    application.include_router(health_router)
    application.include_router(farm_router)
    application.include_router(identity_router)
    application.include_router(inputs_router)
    application.include_router(runs_router)
    application.include_router(weather_router)

    @application.middleware("http")
    async def private_responses(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # FastAPI's default error includes the rejected input, which may be a password.
        errors = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @application.exception_handler(IdentityError)
    async def identity_error_handler(request: Request, error: IdentityError) -> JSONResponse:
        status = next(
            (
                code
                for kind, code in (
                    (Unauthorized, 401),
                    (Forbidden, 403),
                    (IdentityNotFound, 404),
                    (IdentityConflict, 409),
                    (LoginLimited, 429),
                )
                if isinstance(error, kind)
            ),
            400,
        )
        return JSONResponse(
            status_code=status,
            content={"detail": {"code": error.code, "message": error.message}},
            headers={"Retry-After": "900"} if status == 429 else None,
        )

    @application.exception_handler(FarmError)
    async def farm_error_handler(request: Request, error: FarmError) -> JSONResponse:
        status = (
            404
            if isinstance(error, FarmNotFound)
            else 503
            if isinstance(error, WeatherUnavailable)
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
