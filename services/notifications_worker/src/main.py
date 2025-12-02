"""Entry point for the notifications worker service.

This service listens for events and sends notifications (email, telegram, etc.).
Uses FastStream with Redis for event-driven architecture.
"""

from __future__ import annotations

import asyncio
import logging
import os

from faststream import FastStream
from faststream.redis import RedisBroker
from faststream.redis.parser import BinaryMessageFormatV1

from services.notifications_worker.src.handlers import router

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the notifications worker."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set; please add it to your environment variables")

    broker = RedisBroker(redis_url, message_format=BinaryMessageFormatV1)
    broker.include_router(router)

    app = FastStream(broker)

    logger.info("Starting notifications_worker...")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
