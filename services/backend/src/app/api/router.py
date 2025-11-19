"""Top-level API router composition."""

from fastapi import APIRouter

from shared.generated.routers import users

from .v1 import health

api_router = APIRouter()  # noqa: SPEC001
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router)

__all__ = ["api_router"]
