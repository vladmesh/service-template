"""Top-level API router composition."""

from fastapi import APIRouter

from .v1 import health, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router)

__all__ = ["api_router"]
