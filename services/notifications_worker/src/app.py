"""Заготовка под рабочую логику уведомлений."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Placeholder worker loop; replace with real notification handling."""

    logger.info("notifications_worker started (stub). Replace run_worker with real logic.")
    while True:
        await asyncio.sleep(3600)


def main() -> None:
    """Entrypoint for running the stub worker."""

    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
