"""Integration tests for user CRUD endpoints."""

from __future__ import annotations

from typing import Any, cast

from fastapi import status
from httpx import AsyncClient
import pytest


async def _create_user(
    client: AsyncClient, telegram_id: int = 111, is_admin: bool = False
) -> dict[str, Any]:
    response = await client.post(
        "/users",
        json={"telegram_id": telegram_id, "is_admin": is_admin},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_create_and_get_user(client: AsyncClient) -> None:
    created = await _create_user(client, telegram_id=123456789)

    fetched = await client.get(f"/users/{created['id']}")
    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json()["telegram_id"] == 123456789  # noqa: PLR2004


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient) -> None:
    created = await _create_user(client, telegram_id=1111)
    update_payload = {"telegram_id": 987654321, "is_admin": True}

    updated = await client.put(f"/users/{created['id']}", json=update_payload)
    assert updated.status_code == status.HTTP_200_OK
    body = updated.json()
    assert body["telegram_id"] == 987654321  # noqa: PLR2004
    assert body["is_admin"] is True


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient) -> None:
    created = await _create_user(client, telegram_id=2222)

    deleted = await client.delete(f"/users/{created['id']}")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT

    missing = await client.get(f"/users/{created['id']}")
    assert missing.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_telegram_id(client: AsyncClient) -> None:
    await _create_user(client, telegram_id=42)

    duplicate = await client.post("/users", json={"telegram_id": 42, "is_admin": False})

    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert duplicate.json()["detail"] == "Telegram user already exists"


@pytest.mark.asyncio
async def test_update_user_requires_payload(client: AsyncClient) -> None:
    created = await _create_user(client, telegram_id=77)

    response = await client.put(f"/users/{created['id']}", json={})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "No changes supplied"
