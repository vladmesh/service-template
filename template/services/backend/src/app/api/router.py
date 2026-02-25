"""Top-level API router composition."""

from fastapi import APIRouter

from .routers.debug import router as debug_router
from .routers.users import router as users_router
from .v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users_router)
api_router.include_router(debug_router)

__all__ = ["api_router"]
