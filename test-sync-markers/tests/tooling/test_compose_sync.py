"""Tests for compose_sync module."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import TypeAlias

import pytest

from tests.tooling.conftest import create_python_template

FakeRepo: TypeAlias = tuple[Path, ModuleType, ModuleType, ModuleType]


def _write_services_file(
    root: Path, slug: str = "test_service", service_type: str = "python-fastapi"
) -> None:
    (root / "services.yml").write_text(
        "version: 2\n"
        "services:\n"
        f"  - name: {slug}\n"
        f"    type: {service_type}\n"
        "    description: Test service\n",
        encoding="utf-8",
    )


def test_compose_sync_main(fake_repo: FakeRepo, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test compose_sync main function."""
    root, _scaffold, _compose, _sync = fake_repo
    create_python_template(root)
    _write_services_file(root, slug="test_service")

    # Import after setting up fake repo
    import framework.compose_sync as compose_sync_mod

    result = compose_sync_mod.main()
    assert result == 0

    # Check that compose files were updated
    base_compose = (root / "infra" / "compose.base.yml").read_text(encoding="utf-8")
    assert "test-service" in base_compose or "test_service" in base_compose
