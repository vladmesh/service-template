"""Integration tests for user CRUD endpoints against live backend."""

from __future__ import annotations

from typing import Any, cast

from fastapi import status
from httpx import AsyncClient
import pytest


async def _create_user(
    client: AsyncClient, telegram_id: int = 111, is_admin: bool = False
) -> dict[str, Any]:
    """Helper to create a user via API."""
    response = await client.post(
        "/users",
        json={"telegram_id": telegram_id, "is_admin": is_admin},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_user_crud_flow(client: AsyncClient) -> None:
    """Test complete CRUD flow: create, read, update, delete."""
    created = await _create_user(client, telegram_id=123456789)
    user_id = created["id"]

    fetched = await client.get(f"/users/{user_id}")
    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json()["telegram_id"] == 123456789  # noqa: PLR2004

    update_payload = {"telegram_id": 987654321, "is_admin": True}
    updated = await client.put(f"/users/{user_id}", json=update_payload)
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["telegram_id"] == 987654321  # noqa: PLR2004
    assert updated.json()["is_admin"] is True

    deleted = await client.delete(f"/users/{user_id}")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT

    missing = await client.get(f"/users/{user_id}")
    assert missing.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_telegram_id(client: AsyncClient) -> None:
    """Test that creating user with duplicate telegram_id is rejected."""
    await _create_user(client, telegram_id=42)

    duplicate = await client.post("/users", json={"telegram_id": 42, "is_admin": False})

    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert duplicate.json()["detail"] == "Telegram user already exists"
