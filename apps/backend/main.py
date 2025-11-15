"""Entry point for the backend FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core import configure_logging, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - side effect heavy
    """Configure resources for the application lifespan."""

    configure_logging()
    yield


def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""

    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    @application.get("/health", tags=["health"], summary="Application health check")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
