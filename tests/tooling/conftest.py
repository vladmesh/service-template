"""Shared fixtures for tooling tests."""

from __future__ import annotations

from collections.abc import Generator
import importlib
from pathlib import Path

import pytest

from framework import sync_services
from framework.lib import compose_blocks, service_scaffold


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator:
    """Provide an isolated repo root that tooling modules will use."""

    root = tmp_path / "repo"
    monkeypatch.setenv("SERVICE_TEMPLATE_ROOT", str(root))

    scaffold_mod = importlib.reload(service_scaffold)
    compose_mod = importlib.reload(compose_blocks)
    sync_mod = importlib.reload(sync_services)

    infra_dir = root / "infra"
    infra_dir.mkdir(parents=True, exist_ok=True)

    def _write_compose(path: Path) -> None:
        path.write_text(
            "services:\n"
            f"  {compose_mod.START_MARKER}\n"
            "  # managed services injected here\n"
            f"  {compose_mod.END_MARKER}\n",
            encoding="utf-8",
        )

    _write_compose(infra_dir / "compose.base.yml")
    _write_compose(infra_dir / "compose.dev.yml")
    _write_compose(infra_dir / "compose.tests.unit.yml")

    # Mock the templates directory structure
    # 1. Scaffold templates
    scaffold_templates_root = root / "framework" / "templates" / "scaffold" / "services"
    scaffold_templates_root.mkdir(parents=True, exist_ok=True)

    # 2. Docker templates (needed for sync_services)
    docker_templates_root = root / "framework" / "templates" / "docker"
    docker_templates_root.mkdir(parents=True, exist_ok=True)
    (docker_templates_root / "python-fastapi.Dockerfile.j2").write_text(
        "FROM python:3.11-slim\nEXPOSE 8000\nLABEL service={{ service_name }}\n", encoding="utf-8"
    )
    (docker_templates_root / "python-faststream.Dockerfile.j2").write_text(
        "FROM python:3.11-slim\nLABEL service={{ service_name }}\n", encoding="utf-8"
    )
    (docker_templates_root / "node.Dockerfile.j2").write_text(
        "FROM node:20-alpine\nEXPOSE 4321\nLABEL service={{ service_name }}\n", encoding="utf-8"
    )

    # Create minimal specs for services that need them
    (root / "services").mkdir(exist_ok=True)

    yield root, scaffold_mod, compose_mod, sync_mod

    monkeypatch.delenv("SERVICE_TEMPLATE_ROOT", raising=False)
    importlib.reload(service_scaffold)
    importlib.reload(compose_blocks)
    importlib.reload(sync_services)


def create_python_template(
    root: Path,
    include_docs: bool = False,
    service_type: str = "python-fastapi",
) -> Path:
    """Create a minimal python template under templates/services/{service_type}."""

    template_dir = root / "framework" / "templates" / "scaffold" / "services" / service_type
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "src").mkdir(parents=True, exist_ok=True)
    (template_dir / "tests").mkdir(parents=True, exist_ok=True)
    (template_dir / "Dockerfile").write_text(
        'FROM python:3.11-slim\nLABEL service="__SERVICE_NAME__"\n',
        encoding="utf-8",
    )
    if include_docs:
        (template_dir / "README.md").write_text("Template README", encoding="utf-8")
        (template_dir / "AGENTS.md").write_text("Template AGENTS", encoding="utf-8")
    return template_dir


def create_node_template(root: Path, include_docs: bool = False) -> Path:
    """Create a minimal node template under templates/services/node."""

    template_dir = root / "framework" / "templates" / "scaffold" / "services" / "node"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "src").mkdir(parents=True, exist_ok=True)
    (template_dir / "Dockerfile").write_text(
        'FROM node:20-alpine\nLABEL service="__SERVICE_NAME__"\n',
        encoding="utf-8",
    )
    (template_dir / "package.json").write_text(
        '{"name": "__SERVICE_NAME__"}',
        encoding="utf-8",
    )
    if include_docs:
        (template_dir / "README.md").write_text("Template README", encoding="utf-8")
        (template_dir / "AGENTS.md").write_text("Template AGENTS", encoding="utf-8")
    return template_dir
