"""Unit tests for notifications worker handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest


def test_handler_import() -> None:
    """Test that handlers module can be imported."""
    from services.notifications_worker.src.handlers import handle_user_registered, router

    assert router is not None
    assert handle_user_registered is not None


@pytest.mark.asyncio
async def test_handle_user_registered_logs_event(caplog: pytest.LogCaptureFixture) -> None:
    """Test that handle_user_registered logs the event correctly."""
    import logging

    from shared.generated.schemas import UserRegisteredEvent

    from services.notifications_worker.src.handlers import handle_user_registered

    event = UserRegisteredEvent(
        user_id=123,
        email="test@example.com",
        timestamp=datetime.now(UTC),
    )

    with caplog.at_level(logging.INFO):
        await handle_user_registered(event)

    assert "User registered" in caplog.text
    assert "user_id=123" in caplog.text
    assert "test@example.com" in caplog.text


@pytest.mark.asyncio
async def test_main_requires_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that main raises RuntimeError if REDIS_URL is not set."""
    monkeypatch.delenv("REDIS_URL", raising=False)

    from services.notifications_worker.src.main import main

    with pytest.raises(RuntimeError, match="REDIS_URL is not set"):
        await main()


@pytest.mark.asyncio
async def test_main_starts_faststream(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that main creates and runs FastStream app."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")

    mock_app_run = AsyncMock()

    with (
        patch("services.notifications_worker.src.main.FastStream") as mock_faststream,
        patch("services.notifications_worker.src.main.RedisBroker"),
    ):
        mock_faststream.return_value.run = mock_app_run

        from services.notifications_worker.src.main import main

        await main()

        mock_faststream.assert_called_once()
        mock_app_run.assert_awaited_once()
