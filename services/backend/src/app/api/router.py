"""Top-level API router composition."""

from fastapi import APIRouter
from shared.generated.routers.users import create_router as create_users_router

from services.backend.src.controllers.users import UsersController
from services.backend.src.core.db import get_async_db

from .v1 import health


def get_users_controller_impl() -> UsersController:
    """Dependency to get users controller implementation."""
    return UsersController()


api_router = APIRouter()  # noqa: SPEC001
api_router.include_router(health.router, tags=["health"])

# Create and include users router with injected dependencies
users_router = create_users_router(
    get_db=get_async_db,
    get_controller=get_users_controller_impl,
)
api_router.include_router(users_router)

__all__ = ["api_router"]
