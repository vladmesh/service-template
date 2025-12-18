"""Tests for the debug endpoint.

NOTE: This endpoint is DEPRECATED. Services should publish events directly to Redis.
These tests remain to ensure backward compatibility during transition period.
See: services/tg_bot/src/main.py for the recommended pattern.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import status
from httpx import AsyncClient
import pytest

# Ignore DeprecationWarning for these tests as they verify deprecated functionality
pytestmark = pytest.mark.filterwarnings("ignore:Debug endpoint is deprecated")


@pytest.fixture()
def publish_mock(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Patch publish_command_received with an async mock."""

    mock = AsyncMock()
    monkeypatch.setattr("services.backend.src.controllers.debug.publish_command_received", mock)
    return mock


@pytest.mark.asyncio
async def test_debug_command_returns_payload(client: AsyncClient, publish_mock: AsyncMock) -> None:
    """Ensure /debug/command echoes payload back to caller."""
    payload = {"command": "/command", "args": ["foo", "bar"], "user_id": 123}

    response = await client.post("/debug/command", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED
    body = response.json()

    assert {k: body[k] for k in ("command", "args", "user_id")} == payload
    assert body["timestamp"]


@pytest.mark.asyncio
async def test_debug_command_publishes_event(client: AsyncClient, publish_mock: AsyncMock) -> None:
    """Ensure /debug/command publishes an event with expected payload."""
    payload = {"command": "/command", "args": ["foo", "bar"], "user_id": 123}

    await client.post("/debug/command", json=payload)

    publish_mock.assert_awaited_once()
    (published_event,) = publish_mock.await_args.args

    assert published_event.command == payload["command"]
    assert published_event.args == payload["args"]
    assert published_event.user_id == payload["user_id"]
    assert published_event.timestamp is not None
