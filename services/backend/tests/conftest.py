"""Common pytest fixtures for backend API tests."""

from __future__ import annotations

from collections.abc import Generator
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Ensure the backend uses a lightweight SQLite database for tests.
TESTS_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = TESTS_DIR / ".tmp" / "test.db"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB_PATH}")

from services.backend.src.core.settings import get_settings  # noqa: E402

get_settings.cache_clear()
TEST_DB_PATH.unlink(missing_ok=True)

from services.backend.src.core.db import Base, engine, get_db  # noqa: E402  (after env setup)
from services.backend.src.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Create database schema once per test session."""

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a transactional database session for each test."""

    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def app(db_session: Session) -> Generator[FastAPI, None, None]:
    """Return a FastAPI app with the test database wired in."""

    application = create_app()

    def _get_test_db() -> Generator[Session, None, None]:
        yield db_session

    application.dependency_overrides[get_db] = _get_test_db
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture()
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Return a FastAPI test client backed by the configured app."""

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db() -> Generator[None, None, None]:
    """Ensure the temporary SQLite database file is removed after tests."""

    yield
    TEST_DB_PATH.unlink(missing_ok=True)
