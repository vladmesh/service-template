"""Application lifespan hooks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.backend.core import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - side effect heavy
    """Configure resources for the application lifespan."""

    configure_logging()
    yield
