"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Base settings for the backend application."""

    app_name: str = Field(default="Service Template Backend", env="APP_NAME")
    environment: str = Field(default="development", env="APP_ENV")
    app_secret_key: str = Field(default="please-change-me", env="APP_SECRET_KEY")
    enabled_modules_raw: str = Field(default="", env="ENABLED_MODULES")

    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="service_template", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    postgres_require_ssl: bool = Field(default=False, env="POSTGRES_REQUIRE_SSL")

    sqlalchemy_sync_driver: str = Field(default="postgresql+psycopg", env="SQLALCHEMY_SYNC_DRIVER")
    sqlalchemy_async_driver: str = Field(
        default="postgresql+asyncpg", env="SQLALCHEMY_ASYNC_DRIVER"
    )
    database_url_override: str | None = Field(default=None, env="DATABASE_URL")
    async_database_url_override: str | None = Field(default=None, env="ASYNC_DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

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

    return Settings()
