"""Entry point for the Telegram bot service.

This module wires a minimal python-telegram-bot application that can be
extended with real handlers later on.
"""

from __future__ import annotations

from http import HTTPStatus
import logging
import os
from typing import Final

import httpx
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

API_BASE_URL: Final[str] = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
USERS_ENDPOINT: Final[str] = f"{API_BASE_URL}/users"


def _get_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set; please add it to your environment "
            "or docker-compose overlay before running the bot."
        )
    return token


async def _sync_user_with_backend(telegram_id: int) -> bool | None:
    """Ensure the user exists in the backend or create it if missing."""

    payload = {"telegram_id": telegram_id, "is_admin": False}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(USERS_ENDPOINT, json=payload)
    except httpx.HTTPError:
        LOGGER.exception("Failed to talk to backend when syncing Telegram user")
        return None

    if response.status_code == HTTPStatus.CREATED:
        return True
    if response.status_code == HTTPStatus.CONFLICT:
        return False

    LOGGER.error(
        "Unexpected response from backend when syncing Telegram user: status=%s body=%s",
        response.status_code,
        response.text,
    )
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


def build_application() -> Application:
    """Create the telegram bot application with all handlers wired in."""

    application = ApplicationBuilder().token(_get_token()).build()
    application.add_handler(CommandHandler("start", handle_start))
    return application


def main() -> None:
    """Run the bot until the process receives a termination signal."""

    application = build_application()
    LOGGER.info("Starting telegram bot polling loop")
    application.run_polling()


if __name__ == "__main__":
    main()
