from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from faststream.redis import TestRedisBroker
import pytest

from shared.generated.events import _publisher_user_registered, broker, publish_user_registered
from shared.generated.schemas import UserRegisteredEvent


@pytest.mark.asyncio
async def test_publish_user_registered():
    async with TestRedisBroker(broker):
        with patch.object(
            _publisher_user_registered, "publish", new_callable=AsyncMock
        ) as mock_publish:
            event = UserRegisteredEvent(
                user_id=123,
                email="test@example.com",
                timestamp=datetime.now(UTC),
            )

            await publish_user_registered(event)

            mock_publish.assert_called_with(event)
