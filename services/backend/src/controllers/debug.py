from __future__ import annotations

from datetime import UTC, datetime

from shared.generated.events import publish_command_received
from shared.generated.schemas import CommandReceived, CommandReceivedCreate
from sqlalchemy.ext.asyncio import AsyncSession

from ..generated.protocols import DebugControllerProtocol


class DebugController(DebugControllerProtocol):
    """
    Implementation of DebugControllerProtocol.
    """

    async def command(
        self,
        session: AsyncSession,  # noqa: ARG002
        payload: CommandReceivedCreate,
    ) -> CommandReceived:
        """
        Publish a debug command to the message broker and echo the event payload.
        """
        event = CommandReceived(
            command=payload.command,
            args=payload.args,
            user_id=payload.user_id,
            timestamp=payload.timestamp or datetime.now(UTC),
        )
        await publish_command_received(event)
        return event
