"""Common pytest fixtures for backend API tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
import os
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure the backend uses a lightweight SQLite database for tests.
TESTS_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = TESTS_DIR / ".tmp" / "test.db"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH}")
os.environ.setdefault("ASYNC_DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH}")

# Set required environment variables for tests
os.environ.setdefault("APP_NAME", "test-backend")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")

from services.backend.src.core.settings import get_settings  # noqa: E402

get_settings.cache_clear()
TEST_DB_PATH.unlink(missing_ok=True)

from services.backend.src.core.db import Base, get_async_db  # noqa: E402  (after env setup)
from services.backend.src.main import create_app  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create database schema once per test session."""

    engine = create_async_engine(f"sqlite+aiosqlite:///{TEST_DB_PATH}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for each test."""

    connection = await db_engine.connect()
    transaction = await connection.begin()
    session_maker = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    session = session_maker()
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture()
async def app(db_session: AsyncSession) -> AsyncGenerator[FastAPI, None]:
    """Return a FastAPI app with the test database wired in."""

    application = create_app()
    # Patch broker connect/close to avoid requiring a live Redis instance in unit tests
    import importlib

    app_lifespan_module = importlib.import_module("services.backend.src.app.lifespan")

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        # Use savepoint to make changes visible within the test transaction
        async with db_session.begin_nested():
            yield db_session
            await db_session.flush()

    application.dependency_overrides[get_async_db] = _get_test_db
    original_connect = app_lifespan_module.broker.connect
    original_close = app_lifespan_module.broker.close
    app_lifespan_module.broker.connect = AsyncMock()
    app_lifespan_module.broker.close = AsyncMock()
    try:
        yield application
    finally:
        application.dependency_overrides.clear()
        app_lifespan_module.broker.connect = original_connect
        app_lifespan_module.broker.close = original_close


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Return an async HTTP client backed by the configured app."""

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db() -> Generator[None, None, None]:
    """Ensure the temporary SQLite database file is removed after tests."""

    yield
    TEST_DB_PATH.unlink(missing_ok=True)
