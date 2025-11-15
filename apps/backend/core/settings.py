"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Base settings for the backend application."""

    app_name: str = Field(default="Service Template Backend", env="APP_NAME")
    environment: str = Field(default="development", env="APP_ENV")
    database_url: str = Field(default="sqlite:///./backend.db", env="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    return Settings()
