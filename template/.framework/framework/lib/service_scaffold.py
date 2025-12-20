"""Helpers for generating service artifacts from the spec."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any

from framework.lib.env import get_repo_root

ROOT = get_repo_root()

TEMPLATES_DIR = ROOT / "framework" / "templates" / "scaffold" / "services"
SERVICES_ROOT = ROOT / "services"
PLACEHOLDER = "__SERVICE_NAME__"


@dataclass
class ServiceSpec:
    """Minimal description of a service from services.yml."""

    slug: str
    service_type: str
    description: str
    create_dev_template: bool = True
    scaffold_enabled: bool = True
    depends_on: dict[str, str] | None = None
    profiles: list[str] | None = None


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


def build_service_specs(registry: dict[str, Any]) -> list[ServiceSpec]:
    """Convert services.yml data into ServiceSpec objects."""

    specs: list[ServiceSpec] = []
    services = registry.get("services", [])
    if not isinstance(services, list):
        return specs
    for entry in services:
        if not isinstance(entry, dict):
            continue
        slug = entry.get("name")
        service_type = entry.get("type")
        description = (entry.get("description") or "").strip()
        create_dev = entry.get("dev_template", True)
        scaffold_enabled = entry.get("scaffold", True)
        depends_on = entry.get("depends_on")
        profiles = entry.get("profiles")
        if not isinstance(slug, str) or not isinstance(service_type, str):
            continue
        specs.append(
            ServiceSpec(
                slug=slug,
                service_type=service_type,
                description=description or f"{slug.replace('_', ' ').title()} service",
                create_dev_template=bool(create_dev),
                scaffold_enabled=bool(scaffold_enabled),
                depends_on=depends_on if isinstance(depends_on, dict) else None,
                profiles=profiles if isinstance(profiles, list) else None,
            )
        )
    return specs


def scaffold_service(spec: ServiceSpec, *, apply: bool = True) -> ScaffoldReport:
    """Ensure the filesystem artifacts for the service exist."""

    report = ScaffoldReport()
    if not spec.scaffold_enabled:
        return report
    SERVICES_ROOT.mkdir(parents=True, exist_ok=True)

    dest = SERVICES_ROOT / spec.slug
    _ensure_service_tree(spec, dest, apply, report)
    _ensure_service_docs(spec, dest, apply, report)
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
        lambda path: _write_stub(path, readme_stub),
        apply,
        report,
    )
    _ensure_file(
        dest / "AGENTS.md",
        lambda path: _write_stub(path, agents_stub),
        apply,
        report,
    )


def _write_stub(path: Path, contents: str) -> None:
    """Write stub text to a file."""

    path.write_text(contents, encoding="utf-8")


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
