"""Common pytest fixtures for integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from httpx import AsyncClient
import pytest_asyncio

BACKEND_URL = "http://backend:8000"
MAX_WAIT_TIME = 60.0
INITIAL_RETRY_DELAY = 0.5
HEALTH_CHECK_TIMEOUT = 5.0
LOG_WINDOW = 5.0
HTTP_OK = 200


async def wait_for_backend(client: AsyncClient, max_wait: float = MAX_WAIT_TIME) -> None:
    """
    Wait for backend to be ready by checking health endpoint.

    Uses exponential backoff with max wait time.
    """
    delay = INITIAL_RETRY_DELAY
    elapsed = 0.0

    while elapsed < max_wait:
        try:
            response = await client.get("/health", timeout=HEALTH_CHECK_TIMEOUT)
            if response.status_code == HTTP_OK:
                return
        except Exception as e:
            # Log first few attempts for debugging
            if elapsed < LOG_WINDOW:
                print(
                    f"Waiting for backend... (attempt at {elapsed:.1f}s, error: {type(e).__name__})"
                )

        await asyncio.sleep(delay)
        elapsed += delay
        delay = min(delay * 2, 5.0)

    raise RuntimeError(f"Backend at {BACKEND_URL} did not become ready within {max_wait}s")


@pytest_asyncio.fixture(scope="session")
async def backend_ready() -> AsyncGenerator[None, None]:
    """
    Session-scoped fixture that waits for backend to be ready before tests.

    This ensures backend is available before any test runs.
    """
    async with AsyncClient(base_url=BACKEND_URL, timeout=10.0) as client:
        await wait_for_backend(client)
    yield


@pytest_asyncio.fixture
async def client(backend_ready: None) -> AsyncGenerator[AsyncClient, None]:
    """
    Return an async HTTP client connected to the live backend.

    Depends on backend_ready to ensure backend is available.
    """
    async with AsyncClient(
        base_url=BACKEND_URL, timeout=10.0, follow_redirects=True
    ) as test_client:
        yield test_client
