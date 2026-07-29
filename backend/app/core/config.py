from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central application configuration for NEXUS ONE."""

    app_name: str = "NEXUS ONE API"
    app_version: str = "0.2.0"
    app_description: str = "Enterprise Operations Intelligence Platform"

    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"

    database_url: str

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Create and cache one settings object for the application."""
    return Settings()


settings = get_settings()
