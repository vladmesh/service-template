#!/usr/bin/env python3
"""Emit derived metadata (logs/tests) based on services.yml + compose files."""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path
import sys
from typing import Any

import yaml

from framework.lib.compose_blocks import compose_template_for_spec
from framework.lib.env import get_repo_root
from framework.lib.service_scaffold import build_service_specs

ROOT = get_repo_root()
SERVICES_ROOT = ROOT / "services"
UNIT_COMPOSE_FILE = ROOT / "infra" / "compose.tests.unit.yml"
INTEGRATION_COMPOSE_FILE = ROOT / "infra" / "compose.tests.integration.yml"
SPECIAL_PATHS = {"integration": ROOT / "tests"}


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_registry(path: Path = ROOT / "services.yml") -> dict[str, Any]:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("services.yml must start with a mapping")
    return data


def iter_services(registry: dict[str, Any]) -> list[dict[str, Any]]:
    services = registry.get("services", [])
    if not isinstance(services, list):
        return []
    return [service for service in services if isinstance(service, dict)]


def service_path(slug: str) -> Path:
    return SPECIAL_PATHS.get(slug, SERVICES_ROOT / slug)


def gather_logs(registry: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in build_service_specs(registry):
        template = compose_template_for_spec(spec)
        if not template or not template.base:
            continue
        mapping[spec.slug] = spec.slug
    return mapping


@lru_cache(maxsize=2)
def load_compose_services(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = load_yaml(path)
    if not isinstance(data, dict):
        return {}
    services = data.get("services", {})
    return services if isinstance(services, dict) else {}


def gather_tests(registry: dict[str, Any]) -> list[dict[str, str]]:
    tests: list[dict[str, str]] = []
    unit_services = load_compose_services(UNIT_COMPOSE_FILE)

    for service in iter_services(registry):
        slug = service.get("name")
        if not isinstance(slug, str):
            continue
        if slug == "integration":
            integration_services = load_compose_services(INTEGRATION_COMPOSE_FILE)
            if "integration-tests" in integration_services:
                tests.append(
                    {
                        "name": slug,
                        "compose_file": str(INTEGRATION_COMPOSE_FILE.relative_to(ROOT)),
                        "compose_project": "tests-integration",
                        "compose_service": "integration-tests",
                        "mode": "up",
                    }
                )
            continue

        unit_service = slug.replace("_", "-") + "-tests-unit"
        if unit_service not in unit_services:
            continue
        tests.append(
            {
                "name": slug,
                "compose_file": str(UNIT_COMPOSE_FILE.relative_to(ROOT)),
                "compose_project": "tests-unit",
                "compose_service": unit_service,
                "mode": "run",
            }
        )
    return tests


def cmd_logs(args: argparse.Namespace) -> int:
    registry = load_registry()
    mapping = gather_logs(registry)
    if args.service:
        target = mapping.get(args.service)
        if target is None:
            print(f"Unknown service for logs: {args.service}", file=sys.stderr)
            return 1
        print(f"{args.service} {target}")
        return 0
    if not mapping:
        print("No services with log targets found", file=sys.stderr)
        return 1
    for name, compose_service in mapping.items():
        print(f"{name} {compose_service}")
    return 0


def cmd_tests(args: argparse.Namespace) -> int:
    registry = load_registry()
    tests = gather_tests(registry)
    suite = args.suite
    if suite and suite != "all":
        tests = [test for test in tests if test["name"] == suite]
        if not tests:
            print(f"Unknown test suite: {suite}", file=sys.stderr)
            return 1
    if not tests:
        print("No tests configured for services.yml", file=sys.stderr)
        return 1
    for test in tests:
        print(
            f"{test['name']} {test['compose_project']} {test['compose_file']} "
            f"{test['compose_service']} {test.get('mode', 'run')}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit derived service metadata")
    subparsers = parser.add_subparsers(dest="command", required=True)

    logs_parser = subparsers.add_parser("logs", help="List log-capable services")
    logs_parser.add_argument("--service", help="Specific service to query")
    logs_parser.set_defaults(func=cmd_logs)

    tests_parser = subparsers.add_parser(
        "tests", help="List test suites (name project file service mode)"
    )
    tests_parser.add_argument("--suite", help="Filter by suite name")
    tests_parser.set_defaults(func=cmd_tests)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
