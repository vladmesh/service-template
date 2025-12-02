"""Event handlers for notifications worker."""

from __future__ import annotations

import logging

from faststream.redis import RedisRouter
from shared.generated.schemas import UserRegisteredEvent

logger = logging.getLogger(__name__)

router = RedisRouter()


@router.subscriber("user_registered")
async def handle_user_registered(event: UserRegisteredEvent) -> None:
    """Handle user registration event and send welcome notification.

    TODO: Implement actual notification logic (email, telegram, etc.)
    """
    logger.info(
        "User registered: user_id=%s, email=%s, timestamp=%s",
        event.user_id,
        event.email,
        event.timestamp,
    )
