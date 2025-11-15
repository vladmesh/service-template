"""Entry point for the Telegram bot service.

This module wires a minimal python-telegram-bot application that can be
extended with real handlers later on.
"""
from __future__ import annotations

import logging
import os
from typing import Final

from telegram import Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

DEFAULT_GREETING: Final[str] = (
    "Hello! I am the service-template bot. "
    "Customize me inside apps/tg_bot/main.py."
)


def _get_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set; please add it to your environment "
            "or docker-compose overlay before running the bot."
        )
    return token


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to the /start command with a friendly greeting."""

    user_first_name = update.effective_user.first_name if update.effective_user else "there"
    if update.message:
        await update.message.reply_text(
            f"{DEFAULT_GREETING}\nNice to meet you, {user_first_name}!"
        )
    LOGGER.info(
        "Handled /start for user_id=%s",
        update.effective_user.id if update.effective_user else "unknown",
    )


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
