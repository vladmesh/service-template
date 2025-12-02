from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from .app import run_worker

logger = logging.getLogger(__name__)

app = FastAPI(title="Notifications Worker")


@app.on_event("startup")
async def startup_event() -> None:
    """
    Start background worker on application startup.

    Replace this with a proper task manager (e.g., anyio.create_task_group)
    once real notification logic is added.
    """

    logger.info("Starting notifications worker stub")
    import asyncio

    asyncio.create_task(run_worker())


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness probe endpoint."""

    return {"status": "ok"}
