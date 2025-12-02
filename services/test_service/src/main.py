import asyncio
import logging
import os

from faststream import FastStream
from faststream.redis import RedisBroker
from faststream.redis.parser import BinaryMessageFormatV1

from services.test_service.src.controllers.commands import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set; please add it to your environment variables")
    broker = RedisBroker(redis_url, message_format=BinaryMessageFormatV1)

    broker.include_router(router)

    app = FastStream(broker)

    logger.info("Starting test_service...")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
