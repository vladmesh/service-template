#!/usr/bin/env python3
"""Create or validate service artifacts based on services.yml."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from scripts.lib.compose_blocks import (
    COMPOSE_TARGETS,
    ROOT,
    build_service_block,
    load_registry,
    render_service_templates,
    replace_block,
)
from scripts.lib.service_scaffold import ServiceSpec, build_service_specs, scaffold_service


@dataclass
class AggregateReport:
    """Aggregates scaffold results across services."""

    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def merge(self, spec_report) -> None:
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


def run_sync(apply: bool) -> int:
    registry = load_registry()
    specs = build_service_specs(registry)
    report = ensure_artifacts(specs, apply=apply)
    compose_drift = sync_compose(specs, apply=apply)

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
