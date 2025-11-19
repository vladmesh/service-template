"""Shared fixtures for tooling tests."""

from __future__ import annotations

from collections.abc import Generator
import importlib
from pathlib import Path

import pytest

from scripts import sync_services
from scripts.lib import compose_blocks, service_scaffold


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

    templates_root = root / "templates" / "services"
    templates_root.mkdir(parents=True, exist_ok=True)

    yield root, scaffold_mod, compose_mod, sync_mod

    monkeypatch.delenv("SERVICE_TEMPLATE_ROOT", raising=False)
    importlib.reload(service_scaffold)
    importlib.reload(compose_blocks)
    importlib.reload(sync_services)


def create_python_template(root: Path, include_docs: bool = False) -> Path:
    """Create a minimal python template under templates/services/python."""

    template_dir = root / "templates" / "services" / "python"
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
