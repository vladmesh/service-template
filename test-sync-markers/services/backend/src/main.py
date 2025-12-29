"""ASGI entry point for the backend FastAPI application."""

from .app import create_app

app = create_app()
