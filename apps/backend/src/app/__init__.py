"""Application factory for the backend service."""

from fastapi import FastAPI

from ..core import get_settings
from .api.router import api_router
from .lifespan import lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.include_router(api_router)
    return application


__all__ = ["create_app"]
