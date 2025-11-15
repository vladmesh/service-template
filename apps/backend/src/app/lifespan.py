"""Application lifespan hooks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..core import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # pragma: no cover - side effect heavy
    """Configure resources for the application lifespan."""

    configure_logging()
    yield
