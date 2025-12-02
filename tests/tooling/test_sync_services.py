"""Integration-style tests for sync_services CLI."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import TypeAlias

import pytest

from tests.tooling.conftest import create_python_template

FakeRepo: TypeAlias = tuple[Path, ModuleType, ModuleType, ModuleType]


def _write_services_file(root: Path, slug: str = "omega", dev_template: bool = True) -> None:
    dev_line = (
        f"    dev_template: {str(dev_template).lower()}\n" if dev_template is not None else ""
    )
    (root / "services.yml").write_text(
        "version: 2\n"
        "services:\n"
        f"  - name: {slug}\n"
        "    type: python\n"
        "    description: Test service\n"
        f"{dev_line}",
        encoding="utf-8",
    )


def test_sync_services_create_and_check_flow(fake_repo: FakeRepo) -> None:
    root, _scaffold, _compose, sync_mod = fake_repo
    create_python_template(root)
    _write_services_file(root, slug="omega", dev_template=True)

    check_result = sync_mod.run_sync(apply=False)
    assert check_result == 1
    service_dir = root / "services" / "omega"
    assert not service_dir.exists()

    create_result = sync_mod.run_sync(apply=True)
    assert create_result == 0
    assert service_dir.exists()
    base_compose = (root / "infra" / "compose.base.yml").read_text(encoding="utf-8")
    assert "omega" in base_compose
    dev_compose = (root / "infra" / "compose.dev.yml").read_text(encoding="utf-8")
    assert "omega" in dev_compose
    tests_compose = (root / "infra" / "compose.tests.unit.yml").read_text(encoding="utf-8")
    assert "omega-tests-unit" in tests_compose

    final_check = sync_mod.run_sync(apply=False)
    assert final_check == 0

    # rerun with dev_template disabled
    _write_services_file(root, slug="omega", dev_template=False)
    sync_mod.run_sync(apply=True)
    dev_compose = (root / "infra" / "compose.dev.yml").read_text(encoding="utf-8")
    assert "omega" not in dev_compose


def test_sync_services_flags_unscoped_dockerfile_copy(
    fake_repo: FakeRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _scaffold, _compose, sync_mod = fake_repo
    create_python_template(root)
    _write_services_file(root, slug="omega", dev_template=True)

    sync_mod.run_sync(apply=True)
    dockerfile = root / "services" / "omega" / "Dockerfile"
    # We must overwrite the generated Dockerfile with a bad one to trigger the violation
    dockerfile.write_text(
        "FROM python:3.11-slim\nCOPY services ./services\n",
        encoding="utf-8",
    )

    exit_code = sync_mod.run_sync(apply=False)
    captured = capsys.readouterr().out
    assert exit_code == 1
    assert "services/omega/Dockerfile" in captured
