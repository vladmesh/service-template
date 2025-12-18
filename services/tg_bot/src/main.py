"""Entry point for the Telegram bot service.

This module wires a minimal python-telegram-bot application that can be
extended with real handlers later on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
import logging
import os
from typing import Final

import httpx
from shared.generated.events import broker, publish_command_received
from shared.generated.schemas import CommandReceived
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

DEFAULT_GREETING: Final[str] = (
    "Привет! Мы Service Template и этот бот помогает подключиться к нашему сервису."
)
WELCOME_BACK_GREETING: Final[str] = "Хай, добро пожаловать назад!"
REGISTRATION_ERROR: Final[str] = (
    "Не получилось зарегистрировать вас в сервисе, попробуйте ещё раз позже."
)


_api_base_url = os.getenv("API_BASE_URL")
if not _api_base_url:
    raise RuntimeError("API_BASE_URL is not set; please add it to your environment variables")
API_BASE_URL: Final[str] = _api_base_url.rstrip("/")
USERS_ENDPOINT: Final[str] = f"{API_BASE_URL}/users"


def _get_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set; please add it to your environment "
            "or docker-compose overlay before running the bot."
        )
    return token


async def _sync_user_with_backend(
    telegram_id: int,
    *,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> bool | None:
    """Ensure the user exists in the backend or create it if missing.

    Implements exponential backoff retry for transient errors:
    - httpx.ConnectError: Backend temporarily unavailable
    - 5xx status codes: Server-side errors

    Args:
        telegram_id: Telegram user ID to sync
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds, doubles each retry (default: 1.0)

    Returns:
        True if user was created, False if already exists, None on permanent failure
    """
    import asyncio

    payload = {"telegram_id": telegram_id, "is_admin": False}
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(USERS_ENDPOINT, json=payload)

            # Success cases - don't retry
            if response.status_code == HTTPStatus.CREATED:
                return True
            if response.status_code == HTTPStatus.CONFLICT:
                return False

            # Client errors (4xx except 409) - don't retry
            if HTTPStatus.BAD_REQUEST <= response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR:
                LOGGER.error(
                    "Client error from backend: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                return None

            # Server errors (5xx) - retry with backoff
            LOGGER.warning(
                "Backend returned %s (attempt %d/%d), retrying in %.1fs...",
                response.status_code,
                attempt + 1,
                max_retries,
                delay,
            )

        except httpx.ConnectError:
            LOGGER.warning(
                "Backend unavailable (attempt %d/%d), retrying in %.1fs...",
                attempt + 1,
                max_retries,
                delay,
            )
        except httpx.HTTPError:
            LOGGER.exception(
                "HTTP error syncing Telegram user (attempt %d/%d)",
                attempt + 1,
                max_retries,
            )
            if attempt == max_retries - 1:
                return None

        # Wait before next attempt (skip wait on last attempt)
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff

    LOGGER.error("Failed to sync user after %d attempts", max_retries)
    return None


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to the /start command with a friendly greeting."""

    telegram_user = update.effective_user
    if telegram_user is None or telegram_user.id is None:
        LOGGER.warning("/start received without a valid Telegram user")
        return

    sync_result = await _sync_user_with_backend(telegram_user.id)
    if sync_result is None:
        reply_text = REGISTRATION_ERROR
    elif sync_result:
        reply_text = (
            f"{DEFAULT_GREETING}\nРады познакомиться, {telegram_user.first_name or 'друг'}!"
        )
    else:
        reply_text = f"{WELCOME_BACK_GREETING} {telegram_user.first_name or ''}".strip()

    if update.message:
        await update.message.reply_text(reply_text)
    LOGGER.info("Handled /start for user_id=%s", telegram_user.id)


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /command and publish event directly to Redis."""
    telegram_user = update.effective_user
    if telegram_user is None or update.message is None:
        return

    command = update.message.text or "/command"
    args = context.args or []

    event = CommandReceived(
        command=command,
        args=args,
        user_id=telegram_user.id,
        timestamp=datetime.now(UTC),
    )

    try:
        await publish_command_received(event)
        await update.message.reply_text("Command published!")
        LOGGER.info("Published command event: %s", event.command)
    except Exception:
        LOGGER.exception("Failed to publish command event")
        await update.message.reply_text("Failed to send command.")


async def post_init(application: Application) -> None:
    """Connect to Redis broker after application init."""
    await broker.connect()
    LOGGER.info("Connected to Redis broker")


async def post_shutdown(application: Application) -> None:
    """Disconnect from Redis broker on shutdown."""
    await broker.close()
    LOGGER.info("Disconnected from Redis broker")


def build_application() -> Application:
    """Create the telegram bot application with all handlers wired in."""

    application = (
        ApplicationBuilder()
        .token(_get_token())
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("command", handle_command))
    return application


def main() -> None:
    """Run the bot until the process receives a termination signal."""

    application = build_application()
    LOGGER.info("Starting telegram bot polling loop")
    application.run_polling()


if __name__ == "__main__":
    main()
