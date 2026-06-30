from __future__ import annotations

import asyncio

from faststream import FastStream
import structlog

from services.notifications_worker.src.controllers.notifications import NotificationsController
from services.notifications_worker.src.generated.event_adapter import create_event_adapter
from shared.generated.events import get_broker
from shared.logging import configure_logging

configure_logging(service_name="notifications_worker")
logger = structlog.stdlib.get_logger()


async def main() -> None:
    """Run the notifications worker."""
    # Reuse the canonical broker so publishers and subscribers share one
    # wire format (BinaryMessageFormatV1) and one REDIS_URL read.
    broker = get_broker()

    # Stateless worker: no DB session, so create_event_adapter is called
    # without get_session and handlers run without a session/commit.
    create_event_adapter(
        broker=broker,
        get_notifications_controller=lambda: NotificationsController(),
    )

    app = FastStream(broker)

    logger.info("Starting notifications_worker...")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
