"""Validated application settings with redacted database credentials."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load typed API configuration with redacted credentials from CROP_TWIN_* variables."""

    model_config = SettingsConfigDict(env_prefix="CROP_TWIN_", extra="ignore")
    environment: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr = SecretStr("sqlite:///./runtime/crop_twin.db")
    cookie_secure: bool = False
    allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5179",
        "http://localhost:5179",
    ]
