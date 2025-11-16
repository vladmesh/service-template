"""Integration-style tests for sync_services CLI."""

from __future__ import annotations

from pathlib import Path

from tests.tooling.conftest import create_python_template


def _write_services_file(root: Path, slug: str = "omega") -> None:
    (root / "services.yml").write_text(
        "version: 2\n"
        "services:\n"
        f"  - name: {slug}\n"
        "    type: python\n"
        "    description: Test service\n",
        encoding="utf-8",
    )


def test_sync_services_create_and_check_flow(fake_repo) -> None:
    root, _scaffold, _compose, sync_mod = fake_repo
    create_python_template(root)
    _write_services_file(root, slug="omega")

    check_result = sync_mod.run_sync(apply=False)
    assert check_result == 1
    service_dir = root / "services" / "omega"
    assert not service_dir.exists()

    create_result = sync_mod.run_sync(apply=True)
    assert create_result == 0
    assert service_dir.exists()
    base_compose = root / "infra" / "compose.base.yml"
    assert "omega" in base_compose.read_text(encoding="utf-8")

    final_check = sync_mod.run_sync(apply=False)
    assert final_check == 0

    base_template = root / "infra" / "compose.services" / "omega" / "base.yml"
    dev_template = root / "infra" / "compose.services" / "omega" / "dev.yml"
    assert base_template.exists()
    assert dev_template.exists()
