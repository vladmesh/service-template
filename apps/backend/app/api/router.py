"""Top-level API router composition."""

from fastapi import APIRouter

from .v1 import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

__all__ = ["api_router"]
