"""Unit tests for service scaffolding helpers."""

from __future__ import annotations

from pathlib import Path

from tests.tooling.conftest import create_python_template


def _service_paths(root: Path, slug: str) -> tuple[Path, Path, Path]:
    services_root = root / "services" / slug
    base = root / "infra" / "compose.services" / slug / "base.yml"
    dev = root / "infra" / "compose.services" / slug / "dev.yml"
    return services_root, base, dev


def test_scaffold_creates_expected_artifacts(fake_repo) -> None:
    root, scaffold_mod, _compose, _sync = fake_repo
    create_python_template(root, include_docs=False)
    spec = scaffold_mod.ServiceSpec(
        slug="alpha",
        service_type="python",
        description="Alpha service",
    )

    report = scaffold_mod.scaffold_service(spec, apply=True)

    service_dir, base_path, dev_path = _service_paths(root, "alpha")
    assert service_dir.exists()
    dockerfile = (service_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "alpha" in dockerfile and "__SERVICE_NAME__" not in dockerfile
    assert (service_dir / "README.md").read_text(encoding="utf-8").startswith("# Alpha")
    assert (service_dir / "AGENTS.md").exists()

    base_content = base_path.read_text(encoding="utf-8")
    assert "services/alpha/Dockerfile" in base_content
    dev_content = dev_path.read_text(encoding="utf-8")
    assert "extends" in dev_content and "alpha" in dev_content

    assert set(report.created) == {
        str(service_dir.relative_to(root)),
        str((service_dir / "README.md").relative_to(root)),
        str((service_dir / "AGENTS.md").relative_to(root)),
        str(base_path.relative_to(root)),
        str(dev_path.relative_to(root)),
    }
    assert not report.errors
    assert not report.missing


def test_scaffold_reports_missing_when_dry_run(fake_repo) -> None:
    root, scaffold_mod, _compose, _sync = fake_repo
    create_python_template(root, include_docs=False)
    spec = scaffold_mod.ServiceSpec(
        slug="beta",
        service_type="python",
        description="Beta service",
    )

    report = scaffold_mod.scaffold_service(spec, apply=False)

    service_dir, base_path, dev_path = _service_paths(root, "beta")
    assert not service_dir.exists()
    assert set(report.missing) == {
        str(service_dir.relative_to(root)),
        str(base_path.relative_to(root)),
        str(dev_path.relative_to(root)),
    }
    assert not report.created


def test_scaffold_preserves_existing_files(fake_repo) -> None:
    root, scaffold_mod, _compose, _sync = fake_repo
    create_python_template(root, include_docs=False)
    spec = scaffold_mod.ServiceSpec(
        slug="gamma",
        service_type="python",
        description="Gamma service",
    )
    # Initial creation
    scaffold_mod.scaffold_service(spec, apply=True)
    service_dir, base_path, dev_path = _service_paths(root, "gamma")
    custom_readme = service_dir / "README.md"
    custom_readme.write_text("Custom README keep me", encoding="utf-8")

    report = scaffold_mod.scaffold_service(spec, apply=True)

    assert custom_readme.read_text(encoding="utf-8") == "Custom README keep me"
    assert set(report.existing) == {
        str(service_dir.relative_to(root)),
        str(custom_readme.relative_to(root)),
        str((service_dir / "AGENTS.md").relative_to(root)),
        str(base_path.relative_to(root)),
        str(dev_path.relative_to(root)),
    }
    assert not report.created
    assert not report.errors


def test_scaffold_reports_unknown_template(fake_repo) -> None:
    root, scaffold_mod, _compose, _sync = fake_repo
    spec = scaffold_mod.ServiceSpec(
        slug="delta",
        service_type="missing",
        description="Missing template",
    )

    report = scaffold_mod.scaffold_service(spec, apply=True)

    assert report.errors == [
        f"Template for type 'missing' not found ({root / 'templates' / 'services' / 'missing'})"
    ]
