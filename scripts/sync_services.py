#!/usr/bin/env python3
"""Create or validate service artifacts based on services.yml."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass, field
import shlex

from scripts.lib.compose_blocks import (
    COMPOSE_TARGETS,
    ROOT,
    build_service_block,
    load_registry,
    render_service_templates,
    replace_block,
)
from scripts.lib.service_scaffold import (
    SERVICES_ROOT,
    ScaffoldReport,
    ServiceSpec,
    build_service_specs,
    scaffold_service,
)


@dataclass
class AggregateReport:
    """Aggregates scaffold results across services."""

    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def merge(self, spec_report: ScaffoldReport) -> None:
        self.created.extend(spec_report.created)
        self.existing.extend(spec_report.existing)
        self.missing.extend(spec_report.missing)
        self.errors.extend(spec_report.errors)

    def has_issues(self) -> bool:
        return bool(self.errors or self.missing)


def ensure_artifacts(specs: list[ServiceSpec], apply: bool) -> AggregateReport:
    report = AggregateReport()
    for spec in specs:
        result = scaffold_service(spec, apply=apply)
        report.merge(result)
    return report


def sync_compose(specs: list[ServiceSpec], apply: bool) -> list[str]:
    drift: list[str] = []
    for target in COMPOSE_TARGETS:
        templates = render_service_templates(specs, target.key)
        block_lines = build_service_block(templates, target.indent)
        compose_path = target.path
        lines = compose_path.read_text(encoding="utf-8").splitlines()
        new_lines = replace_block(lines, block_lines)
        if apply:
            if new_lines != lines:
                compose_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                print(f"Updated {compose_path.relative_to(ROOT)}")
        else:
            if new_lines != lines:
                drift.append(str(compose_path.relative_to(ROOT)))
    return drift


def validate_dockerfiles(specs: list[ServiceSpec]) -> list[str]:
    """Ensure Dockerfiles only copy in-service paths."""

    errors: list[str] = []
    for spec in specs:
        if spec.service_type != "python" or not spec.scaffold_enabled:
            continue
        dockerfile = SERVICES_ROOT / spec.slug / "Dockerfile"
        if not dockerfile.exists():
            continue
        try:
            lines = dockerfile.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or not stripped.upper().startswith("COPY"):
                continue
            sources = tuple(_extract_copy_sources(stripped))
            if not sources:
                continue
            invalid = [src for src in sources if not _is_allowed_copy_source(src, spec.slug)]
            if invalid:
                rel_path = dockerfile.relative_to(ROOT)
                joined = ", ".join(invalid)
                errors.append(
                    f"{rel_path}:{idx} COPY sources [{joined}] must stay under services/{spec.slug}"
                )
    return errors


def _extract_copy_sources(line: str) -> Iterable[str]:
    """Yield COPY sources for host-context copies."""

    try:
        tokens = shlex.split(line, posix=True)
    except ValueError:
        return []
    if not tokens or tokens[0].upper() != "COPY":
        return []
    idx = 1
    has_stage_source = False
    while idx < len(tokens) and tokens[idx].startswith("--"):
        option = tokens[idx].lower()
        if option.startswith("--from=") or option == "--from":
            has_stage_source = True
            break
        idx += 1
    if has_stage_source:
        return []
    if idx >= len(tokens) - 1:
        return []
    return tokens[idx:-1]


def _is_allowed_copy_source(source: str, slug: str) -> bool:
    """Return True if the source path stays within the service directory."""

    if source.startswith("/"):
        return True
    stripped = source
    while stripped.startswith("./"):
        stripped = stripped[2:]
    normalized = stripped
    # Allow shared directory (common code for all services)
    if normalized == "shared" or normalized.startswith("shared/"):
        return True
    allowed = f"services/{slug}"
    if normalized == allowed or normalized.startswith(f"{allowed}/"):
        return True
    return False


def run_sync(apply: bool) -> int:
    registry = load_registry()
    specs = build_service_specs(registry)
    report = ensure_artifacts(specs, apply=apply)
    compose_drift = sync_compose(specs, apply=apply)
    report.errors.extend(validate_dockerfiles(specs))

    if apply:
        if report.errors:
            print("Errors during sync:")
            for msg in report.errors:
                print(f"  - {msg}")
            return 1
        return 0

    failed = False
    if report.errors:
        print("Errors:")
        for msg in report.errors:
            print(f"  - {msg}")
        failed = True
    if report.missing:
        print("Missing artifacts:")
        for item in report.missing:
            print(f"  - {item}")
        failed = True
    if compose_drift:
        print("Compose files out of sync:")
        for path in compose_drift:
            print(f"  - {path}")
        failed = True
    if failed:
        print("Run `make sync-services create` to generate missing files.")
        return 1
    print("Everything is in sync.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync services from services.yml")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", help="Only report missing artifacts")
    check_parser.set_defaults(apply=False)

    create_parser = subparsers.add_parser("create", help="Create missing artifacts")
    create_parser.set_defaults(apply=True)

    parser.set_defaults(apply=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply = getattr(args, "apply", False)
    return run_sync(apply=apply)


if __name__ == "__main__":
    raise SystemExit(main())
