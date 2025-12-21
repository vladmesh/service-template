"""Debug controller for testing event publishing.

DEPRECATED: This endpoint exists for manual testing and backward compatibility only.
Services should publish events directly to Redis using shared.generated.events.
See: services/tg_bot/src/main.py for the recommended pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime
import warnings

from sqlalchemy.ext.asyncio import AsyncSession

from shared.generated.events import publish_command_received
from shared.generated.schemas import CommandReceived, CommandReceivedCreate

from ..generated.protocols import DebugControllerProtocol


class DebugController(DebugControllerProtocol):
    """
    DEPRECATED: Debug controller for testing event publishing.

    This endpoint is kept for manual testing via curl/Postman.
    Production services should publish events directly to Redis.
    """

    async def command(
        self,
        session: AsyncSession,  # noqa: ARG002
        payload: CommandReceivedCreate,
    ) -> CommandReceived:
        """
        Publish a debug command to the message broker and echo the event payload.

        DEPRECATED: Use direct Redis publishing instead.
        """
        warnings.warn(
            "Debug endpoint is deprecated. Services should publish events directly to Redis.",
            DeprecationWarning,
            stacklevel=2,
        )
        event = CommandReceived(
            command=payload.command,
            args=payload.args,
            user_id=payload.user_id,
            timestamp=payload.timestamp or datetime.now(UTC),
        )
        await publish_command_received(event)
        return event
