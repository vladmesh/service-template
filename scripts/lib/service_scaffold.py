"""Helpers for generating service artifacts from the spec."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import shutil

from scripts.lib import ROOT

TEMPLATES_DIR = ROOT / "templates" / "services"
SERVICES_ROOT = ROOT / "services"
COMPOSE_SERVICES_ROOT = ROOT / "infra" / "compose.services"
PLACEHOLDER = "__SERVICE_NAME__"


@dataclass
class ServiceSpec:
    """Minimal description of a service from services.yml."""

    slug: str
    service_type: str
    description: str
    create_dev_template: bool = True


@dataclass
class ScaffoldReport:
    """Tracks what was created, skipped, or missing."""

    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @staticmethod
    def _rel(path: Path) -> str:
        return str(path.relative_to(ROOT))

    def add_created(self, path: Path) -> None:
        self.created.append(self._rel(path))

    def add_existing(self, path: Path) -> None:
        self.existing.append(self._rel(path))

    def add_missing(self, path: Path) -> None:
        self.missing.append(self._rel(path))

    def add_error(self, message: str) -> None:
        self.errors.append(message)


def scaffold_service(spec: ServiceSpec, *, apply: bool = True) -> ScaffoldReport:
    """Ensure the filesystem artifacts for the service exist."""

    report = ScaffoldReport()
    SERVICES_ROOT.mkdir(parents=True, exist_ok=True)

    dest = SERVICES_ROOT / spec.slug
    _ensure_service_tree(spec, dest, apply, report)
    _ensure_service_docs(spec, dest, apply, report)
    _ensure_compose_templates(spec, apply, report)
    return report


def _ensure_service_tree(
    spec: ServiceSpec,
    dest: Path,
    apply: bool,
    report: ScaffoldReport,
) -> None:
    template_dir = TEMPLATES_DIR / spec.service_type
    if not template_dir.exists():
        report.add_error(f"Template for type '{spec.service_type}' not found ({template_dir})")
        return
    if dest.exists():
        report.add_existing(dest)
        return
    if not apply:
        report.add_missing(dest)
        return

    shutil.copytree(template_dir, dest)
    _replace_placeholder(dest, spec.slug)
    report.add_created(dest)


def _replace_placeholder(target_dir: Path, slug: str) -> None:
    for file_path in target_dir.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PLACEHOLDER in text:
            file_path.write_text(text.replace(PLACEHOLDER, slug), encoding="utf-8")


def _ensure_service_docs(
    spec: ServiceSpec,
    dest: Path,
    apply: bool,
    report: ScaffoldReport,
) -> None:
    if not dest.exists():
        return

    readme_stub = f"# {spec.slug.replace('_', ' ').title()}\n\nDescribe the service here.\n"
    agents_stub = (
        f"# AGENTS — {spec.slug}\n\nDocument how automation agents should work with this service.\n"
    )

    _ensure_file(
        dest / "README.md",
        lambda path: path.write_text(readme_stub, encoding="utf-8"),
        apply,
        report,
    )
    _ensure_file(
        dest / "AGENTS.md",
        lambda path: path.write_text(agents_stub, encoding="utf-8"),
        apply,
        report,
    )


def _ensure_compose_templates(spec: ServiceSpec, apply: bool, report: ScaffoldReport) -> None:
    target_dir = COMPOSE_SERVICES_ROOT / spec.slug
    base_path = target_dir / "base.yml"
    dev_path = target_dir / "dev.yml"

    def write_base(path: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_base_compose(spec.slug), encoding="utf-8")

    def write_dev(path: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_dev_compose(spec.slug), encoding="utf-8")

    _ensure_file(base_path, write_base, apply, report)
    if spec.create_dev_template:
        _ensure_file(dev_path, write_dev, apply, report)


def _ensure_file(
    path: Path,
    create_fn: Callable[[Path], None],
    apply: bool,
    report: ScaffoldReport,
) -> None:
    if path.exists():
        report.add_existing(path)
        return
    if not apply:
        report.add_missing(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    create_fn(path)
    report.add_created(path)


def _compose_env_var(slug: str) -> str:
    return f"{slug.upper()}_IMAGE"


def _render_base_compose(slug: str) -> str:
    dockerfile_path = f"services/{slug}/Dockerfile"
    return (
        f"{slug}:\n"
        f"  image: ${{{_compose_env_var(slug)}:-service-template-{slug}:latest}}\n"
        f"  build:\n"
        f"    context: ..\n"
        f"    dockerfile: {dockerfile_path}\n"
        f"  env_file:\n"
        f"    - ../.env\n"
        f"  networks:\n"
        f"    - internal\n"
    )


def _render_dev_compose(slug: str) -> str:
    return (
        f"{slug}:\n"
        f"  extends:\n"
        f"    file: compose.base.yml\n"
        f"    service: {slug}\n"
        f"  volumes:\n"
        f"    - ../:/workspace:delegated\n"
        f"  working_dir: /workspace\n"
        f"  env_file:\n"
        f"    - ../.env\n"
    )
