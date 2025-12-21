"""Top-level API router composition."""

from fastapi import APIRouter

from services.backend.src.controllers.debug import DebugController
from services.backend.src.controllers.users import UsersController
from services.backend.src.core.db import get_async_db
from services.backend.src.generated.registry import create_api_router

from .v1 import health


def get_users_controller() -> UsersController:
    """Dependency to get users controller implementation."""
    return UsersController()


def get_debug_controller() -> DebugController:
    """Dependency to get debug controller implementation."""
    return DebugController()


# Create main API router with health endpoint
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])

# Include all domain routers via auto-generated registry
# Note: get_async_db is AsyncGenerator[AsyncSession, None],
# but FastAPI's Depends handles it correctly
domain_router = create_api_router(
    get_db=get_async_db,  # type: ignore[arg-type]
    get_users_controller=get_users_controller,
    get_debug_controller=get_debug_controller,
)
api_router.include_router(domain_router)

__all__ = ["api_router"]
