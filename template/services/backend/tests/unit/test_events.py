import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from datetime import UTC, datetime

from faststream.redis import TestRedisBroker
import pytest

from shared.generated.events import get_broker, publish_user_registered
from shared.generated.schemas import UserRead


@pytest.mark.asyncio
async def test_publish_user_registered() -> None:
    async with TestRedisBroker(get_broker()):
        event = UserRead(
            id=123,
            telegram_id=456,
            is_admin=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await publish_user_registered(event)
