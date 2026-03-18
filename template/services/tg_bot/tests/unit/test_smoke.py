"""Smoke tests: verify that key modules are importable.

Catches relative-import bugs and missing dependencies that would crash
the container at startup but pass unit tests (which use absolute imports).
"""

from __future__ import annotations


def test_main_importable():
    from services.tg_bot.src.main import build_application

    assert build_application is not None


def test_middleware_importable():
    from services.tg_bot.src.middleware import install_update_logging

    assert install_update_logging is not None
