"""ASGI entry point for the backend FastAPI application."""

from apps.backend.app import create_app

app = create_app()
