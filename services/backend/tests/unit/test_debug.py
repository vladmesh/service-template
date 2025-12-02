from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import status
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_debug_command_publishes_event(client: AsyncClient) -> None:
    """Ensure /debug/command publishes an event and echoes the payload."""
    payload = {"command": "/command", "args": ["foo", "bar"], "user_id": 123}

    with patch(
        "services.backend.src.controllers.debug.publish_command_received",
        new_callable=AsyncMock,
    ) as mock_publish:
        response = await client.post("/debug/command", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()

    assert {k: body[k] for k in ("command", "args", "user_id")} == payload
    assert body["timestamp"]

    mock_publish.assert_awaited_once()
    published_event = mock_publish.await_args.args[0]
    assert (published_event.command, published_event.args, published_event.user_id) == (
        payload["command"],
        payload["args"],
        payload["user_id"],
    )
    assert published_event.timestamp is not None
