"""Tests for request logging middleware and exception handler."""

from __future__ import annotations

import json

from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
import pytest


@pytest.fixture()
def log_app() -> FastAPI:
    """Minimal FastAPI app with logging middleware wired in."""

    from services.backend.src.app.middleware import (
        RequestLoggingMiddleware,
        register_exception_handler,
    )

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handler(app)

    @app.get("/hello")
    async def _hello():
        return {"msg": "hi"}

    @app.get("/health")
    async def _health():
        return {"status": "ok"}

    @app.get("/boom")
    async def _boom():
        raise RuntimeError("test explosion")

    return app


@pytest.fixture()
async def log_client(log_app: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=log_app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_request_logged_with_standard_fields(log_client: AsyncClient, capsys) -> None:
    response = await log_client.get("/hello")

    assert response.status_code == status.HTTP_200_OK

    captured = capsys.readouterr()
    # Find the JSON log line for our request
    log_lines = [line for line in captured.out.strip().splitlines() if line.strip()]
    request_logs = []
    for line in log_lines:
        try:
            parsed = json.loads(line)
            if parsed.get("event") == "request":
                request_logs.append(parsed)
        except json.JSONDecodeError:
            continue

    assert len(request_logs) >= 1, f"Expected request log, got stdout: {captured.out}"
    log = request_logs[-1]
    assert log["method"] == "GET"
    assert log["path"] == "/hello"
    assert log["status_code"] == status.HTTP_200_OK
    assert "duration_ms" in log
    assert "timestamp" in log


@pytest.mark.asyncio
async def test_health_endpoint_not_logged(log_client: AsyncClient, capsys) -> None:
    response = await log_client.get("/health")

    assert response.status_code == status.HTTP_200_OK

    captured = capsys.readouterr()
    for line in captured.out.strip().splitlines():
        try:
            parsed = json.loads(line)
            assert not (parsed.get("event") == "request" and parsed.get("path") == "/health"), (
                "Health endpoint should not be logged"
            )
        except json.JSONDecodeError:
            continue


@pytest.mark.asyncio
async def test_exception_returns_500_and_logs_error(log_client: AsyncClient, capsys) -> None:
    response = await log_client.get("/boom")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Internal server error"}

    captured = capsys.readouterr()
    error_logs = []
    for line in captured.out.strip().splitlines():
        try:
            parsed = json.loads(line)
            if parsed.get("event") == "unhandled_exception":
                error_logs.append(parsed)
        except json.JSONDecodeError:
            continue

    assert len(error_logs) >= 1, f"Expected error log, got stdout: {captured.out}"
    log = error_logs[-1]
    assert log["exception_type"] == "RuntimeError"
    assert "test explosion" in log["exception_message"]


@pytest.mark.asyncio
async def test_user_id_extractor_is_called(capsys) -> None:
    from services.backend.src.app.middleware import (
        RequestLoggingMiddleware,
    )

    app = FastAPI()

    def extract_user(request) -> str | None:
        return "user:42"

    app.add_middleware(RequestLoggingMiddleware, user_id_extractor=extract_user)

    @app.get("/me")
    async def _me():
        return {"user": "me"}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        await c.get("/me")

    captured = capsys.readouterr()
    for line in captured.out.strip().splitlines():
        try:
            parsed = json.loads(line)
            if parsed.get("event") == "request":
                assert parsed["user_id"] == "user:42"
                return
        except json.JSONDecodeError:
            continue

    pytest.fail(f"No request log found in stdout: {captured.out}")
