from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.generated.schemas import UserRegisteredEvent

logger = logging.getLogger(__name__)


class NotificationsController:
    """Controller for notifications logic."""

    async def on_user_registered(
        self,
        session: AsyncSession,
        payload: UserRegisteredEvent,
    ) -> None:
        """Handle user registration."""
        logger.info(
            "Controller handled User registered: user_id=%s, email=%s, timestamp=%s",
            payload.user_id,
            payload.email,
            payload.timestamp,
        )
