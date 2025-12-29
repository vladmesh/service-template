"""Unit tests for command handler with direct Redis publishing."""

from __future__ import annotations

from typing import Final
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

TEST_TELEGRAM_USER_ID: Final[int] = 123456789


@pytest.fixture
def mock_broker() -> MagicMock:
    """Mock the broker for testing."""
    with patch("services.tg_bot.src.main.broker") as mock:
        mock.connect = AsyncMock()
        mock.close = AsyncMock()
        yield mock


@pytest.fixture
def mock_publish() -> AsyncMock:
    """Mock the publish function."""
    with patch("services.tg_bot.src.main.publish_command_received") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_update() -> MagicMock:
    """Create a mock Telegram Update object."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = TEST_TELEGRAM_USER_ID
    update.message = MagicMock()
    update.message.text = "/command test"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Create a mock Context object."""
    context = MagicMock()
    context.args = ["arg1", "arg2"]
    return context


@pytest.mark.asyncio
async def test_handle_command_publishes_event(
    mock_publish: AsyncMock,
    mock_broker: MagicMock,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Test that handle_command publishes event to Redis."""
    from services.tg_bot.src.main import handle_command

    await handle_command(mock_update, mock_context)

    mock_publish.assert_awaited_once()
    published_event = mock_publish.await_args[0][0]

    assert published_event.command == "/command test"
    assert published_event.args == ["arg1", "arg2"]
    assert published_event.user_id == TEST_TELEGRAM_USER_ID
    assert published_event.timestamp is not None

    mock_update.message.reply_text.assert_awaited_once_with("Command published!")


@pytest.mark.asyncio
async def test_handle_command_handles_publish_failure(
    mock_publish: AsyncMock,
    mock_broker: MagicMock,
    mock_update: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Test graceful handling of publish failures."""
    from services.tg_bot.src.main import handle_command

    mock_publish.side_effect = Exception("Redis connection failed")

    await handle_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once_with("Failed to send command.")


@pytest.mark.asyncio
async def test_handle_command_skips_without_user(
    mock_publish: AsyncMock,
    mock_broker: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Test that handler skips if no user is present."""
    from services.tg_bot.src.main import handle_command

    update = MagicMock()
    update.effective_user = None
    update.message = MagicMock()

    await handle_command(update, mock_context)

    mock_publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_command_skips_without_message(
    mock_publish: AsyncMock,
    mock_broker: MagicMock,
    mock_context: MagicMock,
) -> None:
    """Test that handler skips if no message is present."""
    from services.tg_bot.src.main import handle_command

    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123
    update.message = None

    await handle_command(update, mock_context)

    mock_publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_post_init_connects_broker(mock_broker: MagicMock) -> None:
    """Test that post_init connects the broker."""
    from services.tg_bot.src.main import post_init

    app = MagicMock()
    await post_init(app)

    mock_broker.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_shutdown_closes_broker(mock_broker: MagicMock) -> None:
    """Test that post_shutdown closes the broker."""
    from services.tg_bot.src.main import post_shutdown

    app = MagicMock()
    await post_shutdown(app)

    mock_broker.close.assert_awaited_once()


class TestSyncUserWithBackend:
    """Tests for _sync_user_with_backend function."""

    @pytest.mark.asyncio
    async def test_sync_user_created(self) -> None:
        """Test that new user creation returns True."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.CREATED

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            result = await _sync_user_with_backend(TEST_TELEGRAM_USER_ID)
            assert result is True

    @pytest.mark.asyncio
    async def test_sync_user_already_exists(self) -> None:
        """Test that existing user returns False (conflict)."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.CONFLICT

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            result = await _sync_user_with_backend(TEST_TELEGRAM_USER_ID)
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_user_http_error(self) -> None:
        """Test that HTTP errors return None."""
        from unittest.mock import AsyncMock

        import httpx

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            result = await _sync_user_with_backend(TEST_TELEGRAM_USER_ID)
            assert result is None

    @pytest.mark.asyncio
    async def test_sync_user_unexpected_status(self) -> None:
        """Test that unexpected status codes return None."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            mock_response.text = "Internal Server Error"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            # Use minimal retries and delay for faster tests
            result = await _sync_user_with_backend(
                TEST_TELEGRAM_USER_ID, max_retries=1, initial_delay=0.01
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_sync_user_retries_on_5xx(self) -> None:
        """Test that 5xx errors trigger retries with eventual success."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        call_count = 0

        async def post_side_effect(*args, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            success_attempt = 3
            if call_count < success_attempt:
                mock_response.status_code = HTTPStatus.SERVICE_UNAVAILABLE
                mock_response.text = "Service Unavailable"
            else:
                mock_response.status_code = HTTPStatus.CREATED
            return mock_response

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=post_side_effect)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            max_attempts = 3
            result = await _sync_user_with_backend(
                TEST_TELEGRAM_USER_ID, max_retries=max_attempts, initial_delay=0.01
            )
            assert result is True
            assert call_count == max_attempts

    @pytest.mark.asyncio
    async def test_sync_user_retries_on_connect_error(self) -> None:
        """Test that ConnectError triggers retries with eventual success."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        import httpx

        call_count = 0

        async def post_side_effect(*args, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            success_attempt = 2
            if call_count < success_attempt:
                raise httpx.ConnectError("Connection refused")
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.CONFLICT
            return mock_response

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=post_side_effect)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            result = await _sync_user_with_backend(
                TEST_TELEGRAM_USER_ID, max_retries=3, initial_delay=0.01
            )
            expected_attempts = 2
            assert result is False  # User already exists
            assert call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_sync_user_no_retry_on_4xx(self) -> None:
        """Test that 4xx client errors do NOT trigger retries."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        call_count = 0

        async def post_side_effect(*args, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.BAD_REQUEST
            mock_response.text = "Bad Request"
            return mock_response

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=post_side_effect)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            result = await _sync_user_with_backend(
                TEST_TELEGRAM_USER_ID, max_retries=3, initial_delay=0.01
            )
            assert result is None
            assert call_count == 1  # No retries on 4xx

    @pytest.mark.asyncio
    async def test_sync_user_exhausts_all_retries(self) -> None:
        """Test that function returns None after exhausting all retries."""
        from http import HTTPStatus
        from unittest.mock import AsyncMock

        call_count = 0

        async def post_side_effect(*args, **kwargs) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            mock_response.text = "Internal Server Error"
            return mock_response

        with patch("services.tg_bot.src.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=post_side_effect)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            from services.tg_bot.src.main import _sync_user_with_backend

            max_attempts = 3
            result = await _sync_user_with_backend(
                TEST_TELEGRAM_USER_ID, max_retries=max_attempts, initial_delay=0.01
            )
            assert result is None
            assert call_count == max_attempts  # All retries exhausted


class TestHandleStart:
    """Tests for handle_start function."""

    @pytest.fixture
    def mock_sync_user(self) -> AsyncMock:
        """Mock _sync_user_with_backend."""
        with patch("services.tg_bot.src.main._sync_user_with_backend") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_handle_start_new_user(self, mock_sync_user: AsyncMock) -> None:
        """Test greeting for new user."""
        from services.tg_bot.src.main import DEFAULT_GREETING, handle_start

        mock_sync_user.return_value = True

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = TEST_TELEGRAM_USER_ID
        update.effective_user.first_name = "John"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_start(update, context)

        update.message.reply_text.assert_awaited_once()
        call_args = update.message.reply_text.await_args[0][0]
        assert DEFAULT_GREETING in call_args
        assert "John" in call_args

    @pytest.mark.asyncio
    async def test_handle_start_returning_user(self, mock_sync_user: AsyncMock) -> None:
        """Test greeting for returning user."""
        from services.tg_bot.src.main import WELCOME_BACK_GREETING, handle_start

        mock_sync_user.return_value = False

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = TEST_TELEGRAM_USER_ID
        update.effective_user.first_name = "Jane"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_start(update, context)

        update.message.reply_text.assert_awaited_once()
        call_args = update.message.reply_text.await_args[0][0]
        assert WELCOME_BACK_GREETING in call_args

    @pytest.mark.asyncio
    async def test_handle_start_sync_error(self, mock_sync_user: AsyncMock) -> None:
        """Test error message when sync fails."""
        from services.tg_bot.src.main import REGISTRATION_ERROR, handle_start

        mock_sync_user.return_value = None

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = TEST_TELEGRAM_USER_ID
        update.effective_user.first_name = "Bob"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_start(update, context)

        update.message.reply_text.assert_awaited_once_with(REGISTRATION_ERROR)

    @pytest.mark.asyncio
    async def test_handle_start_no_user(self, mock_sync_user: AsyncMock) -> None:
        """Test that handler skips if no user."""
        from services.tg_bot.src.main import handle_start

        update = MagicMock()
        update.effective_user = None
        update.message = MagicMock()

        context = MagicMock()

        await handle_start(update, context)

        mock_sync_user.assert_not_awaited()
