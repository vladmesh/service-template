from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from faststream import FastStream
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from services.notifications_worker.src.controllers.notifications import NotificationsController
from services.notifications_worker.src.generated.event_adapter import create_event_adapter
from shared.generated.events import get_broker
from shared.logging import configure_logging

configure_logging(service_name="notifications_worker")
logger = structlog.stdlib.get_logger()


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Dummy session factory since this worker relies on FastStream mainly."""

    class MockSession:
        async def commit(self) -> None:
            pass

        async def rollback(self) -> None:
            pass

    yield MockSession()  # type: ignore


async def main() -> None:
    """Run the notifications worker."""
    # Reuse the canonical broker so publishers and subscribers share one
    # wire format (BinaryMessageFormatV1) and one REDIS_URL read.
    broker = get_broker()

    # Register unified handlers
    create_event_adapter(
        broker=broker,
        get_session=get_session,
        get_notifications_controller=lambda: NotificationsController(),
    )

    app = FastStream(broker)

    logger.info("Starting notifications_worker...")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
