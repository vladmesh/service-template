"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
import os
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base settings for the backend application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def _validate_required_env_vars(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            "APP_NAME",
            "APP_ENV",
            "APP_SECRET_KEY",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        ]
        missing_vars = []
        for var_name in required_vars:
            value = os.getenv(var_name)
            if not value:
                missing_vars.append(var_name)
        if missing_vars:
            raise RuntimeError(
                f"Required environment variables are not set: {', '.join(missing_vars)}. "
                "Please add them to your environment variables."
            )

    app_name: str = Field(validation_alias="APP_NAME")
    environment: str = Field(validation_alias="APP_ENV")
    app_secret_key: str = Field(validation_alias="APP_SECRET_KEY")
    enabled_modules_raw: str = Field(default="", validation_alias="ENABLED_MODULES")

    postgres_host: str = Field(validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_require_ssl: bool = Field(default=False, validation_alias="POSTGRES_REQUIRE_SSL")

    sqlalchemy_sync_driver: str = Field(
        default="postgresql+psycopg", validation_alias="SQLALCHEMY_SYNC_DRIVER"
    )
    sqlalchemy_async_driver: str = Field(
        default="postgresql+asyncpg", validation_alias="SQLALCHEMY_ASYNC_DRIVER"
    )
    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    async_database_url_override: str | None = Field(
        default=None, validation_alias="ASYNC_DATABASE_URL"
    )

    @property
    def enabled_modules(self) -> list[str]:
        """List of optional modules that should be activated."""

        if not self.enabled_modules_raw:
            return []
        return [module.strip() for module in self.enabled_modules_raw.split(",") if module.strip()]

    @property
    def sync_database_url(self) -> str:
        """SQLAlchemy URL for synchronous usage (ORM, pytest)."""

        if self.database_url_override:
            return self.database_url_override
        return self._build_postgres_url(self.sqlalchemy_sync_driver)

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy URL for async usage (Alembic)."""

        if self.async_database_url_override:
            return self.async_database_url_override
        if self.database_url_override and "+async" in self.database_url_override:
            return self.database_url_override
        return self._build_postgres_url(self.sqlalchemy_async_driver)

    @property
    def database_url(self) -> str:
        """Backward compatible accessor for synchronous SQLAlchemy URL."""

        return self.sync_database_url

    def _build_postgres_url(self, driver: str) -> str:
        """Create a SQLAlchemy URL for the configured Postgres instance."""

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        database = self.postgres_db
        ssl_query = "?sslmode=require" if self.postgres_require_ssl else ""
        return f"{driver}://{user}:{password}@{host}:{port}/{database}{ssl_query}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    settings = Settings()
    settings._validate_required_env_vars()
    return settings
