"""Smoke tests verifying the FastAPI stack is wired correctly."""

from fastapi import status


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
