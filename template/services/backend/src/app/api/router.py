"""Top-level API router composition."""

from fastapi import APIRouter

from services.backend.src.controllers.debug import DebugController
from services.backend.src.controllers.users import UsersController
from services.backend.src.core.db import get_async_db
from services.backend.src.generated.routers.debug import create_router as create_debug_router
from services.backend.src.generated.routers.users import create_router as create_users_router

from .v1 import health


def get_users_controller_impl() -> UsersController:
    """Dependency to get users controller implementation."""
    return UsersController()


def get_debug_controller_impl() -> DebugController:
    """Dependency to get debug controller implementation."""
    return DebugController()


api_router = APIRouter()  # noqa
api_router.include_router(health.router, tags=["health"])

# Create and include users router with injected dependencies
# Note: get_async_db is AsyncGenerator[AsyncSession, None],
# but FastAPI's Depends handles it correctly
users_router = create_users_router(
    get_db=get_async_db,  # type: ignore[arg-type]
    get_controller=get_users_controller_impl,
)
api_router.include_router(users_router)

# Create and include debug router to publish test commands to the broker
debug_router = create_debug_router(
    get_db=get_async_db,  # type: ignore[arg-type]
    get_controller=get_debug_controller_impl,
)
api_router.include_router(debug_router)

__all__ = ["api_router"]
