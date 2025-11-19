"""Integration tests for user CRUD endpoints."""

from __future__ import annotations

from typing import Any, cast

from fastapi import status
from fastapi.testclient import TestClient


def _create_user(
    client: TestClient, telegram_id: int = 111, is_admin: bool = False
) -> dict[str, Any]:
    response = client.post(
        "/users",
        json={"telegram_id": telegram_id, "is_admin": is_admin},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return cast(dict[str, Any], response.json())


def test_user_crud_flow(client: TestClient) -> None:
    created = _create_user(client, telegram_id=123456789)
    user_id = created["id"]

    fetched = client.get(f"/users/{user_id}")
    assert fetched.status_code == status.HTTP_200_OK
    assert fetched.json()["telegram_id"] == 123456789  # noqa: PLR2004

    update_payload = {"telegram_id": 987654321, "is_admin": True}
    updated = client.put(f"/users/{user_id}", json=update_payload)
    assert updated.status_code == status.HTTP_200_OK
    assert updated.json()["telegram_id"] == 987654321  # noqa: PLR2004
    assert updated.json()["is_admin"] is True

    deleted = client.delete(f"/users/{user_id}")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT

    missing = client.get(f"/users/{user_id}")
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_create_user_rejects_duplicate_telegram_id(client: TestClient) -> None:
    _create_user(client, telegram_id=42)

    duplicate = client.post("/users", json={"telegram_id": 42, "is_admin": False})

    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert duplicate.json()["detail"] == "Telegram user already exists"


def test_update_user_requires_payload(client: TestClient) -> None:
    created = _create_user(client, telegram_id=77)

    response = client.put(f"/users/{created['id']}", json={})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "No changes supplied"
