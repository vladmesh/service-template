from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.generated.schemas import UserRead

logger = structlog.stdlib.get_logger()


class NotificationsController:
    """Controller for notifications logic."""

    async def on_user_registered(
        self,
        session: AsyncSession,
        payload: UserRead,
    ) -> None:
        """Handle user registration."""
        logger.info(
            "Controller handled user registered",
            user_id=payload.id,
            telegram_id=payload.telegram_id,
        )
