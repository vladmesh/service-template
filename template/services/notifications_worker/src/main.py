from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

from faststream import FastStream
from faststream.redis import RedisBroker
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from services.notifications_worker.src.controllers.notifications import NotificationsController
from services.notifications_worker.src.generated.event_adapter import create_event_adapter
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
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set; please add it to your environment variables")

    broker = RedisBroker(redis_url)

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
