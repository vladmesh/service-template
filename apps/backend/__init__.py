"""Backend application package exposed for compatibility."""

from .src.main import app, create_app

__all__ = ["app", "create_app"]
