"""Reusable FastAPI dependencies."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from apps.backend.core.db import get_db as _get_db_session


def get_db() -> Generator[Session, None, None]:
    """Return a database session dependency."""

    yield from _get_db_session()


__all__ = ["get_db"]
