"""Unit tests for notifications worker handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from structlog.testing import capture_logs


def test_imports() -> None:
    """Test that modules can be imported."""
    from services.notifications_worker.src.controllers.notifications import (
        NotificationsController,
    )
    from services.notifications_worker.src.generated.event_adapter import create_event_adapter

    assert NotificationsController is not None
    assert create_event_adapter is not None


@pytest.mark.asyncio
async def test_handle_user_registered_logs_event() -> None:
    """Test that handle_user_registered logs the event correctly."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.notifications_worker.src.controllers.notifications import (
        NotificationsController,
    )
    from shared.generated.schemas import UserRegisteredEvent

    event = UserRegisteredEvent(
        user_id=123,
        email="test@example.com",
        timestamp=datetime.now(UTC),
    )

    controller = NotificationsController()
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    with capture_logs() as logs:
        await controller.on_user_registered(session, event)

    assert len(logs) == 1
    assert logs[0]["event"] == "Controller handled user registered"
    assert logs[0]["user_id"] == event.user_id
    assert logs[0]["email"] == event.email


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
        patch("services.notifications_worker.src.main.get_broker"),
    ):
        mock_faststream.return_value.run = mock_app_run

        from services.notifications_worker.src.main import main

        await main()

        mock_faststream.assert_called_once()
        mock_app_run.assert_awaited_once()
