"""Validated local API settings. Database integration is not yet implemented."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load non-secret API settings from CROP_TWIN_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="CROP_TWIN_", extra="ignore")
    environment: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
