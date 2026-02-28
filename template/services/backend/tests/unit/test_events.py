import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from datetime import UTC, datetime

from faststream.redis import TestRedisBroker
import pytest

from shared.generated.events import get_broker, publish_user_registered
from shared.generated.schemas import UserRegisteredEvent


@pytest.mark.asyncio
async def test_publish_user_registered() -> None:
    async with TestRedisBroker(get_broker()):
        event = UserRegisteredEvent(
            user_id=123,
            email="test@example.com",
            timestamp=datetime.now(UTC),
        )

        await publish_user_registered(event)
