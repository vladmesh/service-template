#!/usr/bin/env python3
"""Utility helpers for the services registry (services.yml)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = ROOT / "services.yml"
SERVICES_ROOT = ROOT / "services"
COMPOSE_SERVICES_ROOT = ROOT / "infra" / "compose.services"
UNIT_COMPOSE_FILE = ROOT / "infra" / "compose.tests.unit.yml"
INTEGRATION_COMPOSE_FILE = ROOT / "infra" / "compose.tests.integration.yml"
ALLOWED_TYPES = {"python", "default"}
SPECIAL_SERVICE_PATHS: dict[str, Path] = {"integration": ROOT / "tests"}


@dataclass
class ValidationResult:
    """Represents the outcome of registry validation."""

    ok: bool
    errors: list[str]


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Registry file not found: {path}")
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("Registry root must be a mapping")
    return data


def service_path(slug: str) -> Path:
    return SPECIAL_SERVICE_PATHS.get(slug, SERVICES_ROOT / slug)


def compose_template_path(slug: str, template: str) -> Path:
    return COMPOSE_SERVICES_ROOT / slug / f"{template}.yml"


def slug_to_unit_service(slug: str) -> str:
    return f"{slug.replace('_', '-')}-tests-unit"


def slug_to_compose_service(slug: str) -> str:
    return slug


@lru_cache(maxsize=2)
def load_compose_services(compose_path: Path) -> dict[str, Any]:
    if not compose_path.exists():
        return {}
    data = load_yaml(compose_path)
    if not isinstance(data, dict):
        return {}
    services = data.get("services", {})
    return services if isinstance(services, dict) else {}


def validate_registry(data: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    if data.get("version") != 2:
        errors.append("Registry version must be set to 2")

    services = data.get("services")
    if not isinstance(services, list):
        errors.append("'services' must be a list")
        return ValidationResult(False, errors)

    seen_names: set[str] = set()
    for index, service in enumerate(services):
        prefix = f"services[{index}]"
        if not isinstance(service, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        name = service.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}.name must be a non-empty string")
            continue
        if name in seen_names:
            errors.append(f"Duplicate service name detected: {name}")
            continue
        seen_names.add(name)

        description = service.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{prefix}.description must be a non-empty string")

        type_value = service.get("type")
        if isinstance(type_value, str):
            if type_value not in ALLOWED_TYPES:
                errors.append(f"{prefix}.type must be one of {sorted(ALLOWED_TYPES)}")
        else:
            errors.append(f"{prefix}.type must be a string")

        derived_path = service_path(name)
        if not derived_path.exists():
            errors.append(
                f"{prefix}: derived path does not exist ({derived_path.relative_to(ROOT)})"
            )

    return ValidationResult(not errors, errors)


def cmd_validate(args: argparse.Namespace) -> int:
    data = load_registry(args.path)
    result = validate_registry(data)
    if not result.ok:
        for message in result.errors:
            print(f"ERROR: {message}", file=sys.stderr)
        return 1
    print(f"Registry validated successfully ({len(data.get('services', []))} services)")
    return 0


def iter_services(data: dict[str, Any]) -> list[dict[str, Any]]:
    services = data.get("services", [])
    if not isinstance(services, list):
        return []
    return [service for service in services if isinstance(service, dict)]


def gather_log_targets(data: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for service in iter_services(data):
        slug = service.get("name")
        if not isinstance(slug, str):
            continue
        if not compose_template_path(slug, "base").exists():
            continue
        mapping[slug] = slug_to_compose_service(slug)
    return mapping


def iter_tests(data: dict[str, Any]) -> list[dict[str, str]]:
    tests: list[dict[str, str]] = []
    unit_services = load_compose_services(UNIT_COMPOSE_FILE)
    integration_services = load_compose_services(INTEGRATION_COMPOSE_FILE)

    for service in iter_services(data):
        slug = service.get("name")
        if not isinstance(slug, str):
            continue
        if slug == "integration":
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
        compose_service = slug_to_unit_service(slug)
        if compose_service not in unit_services:
            continue
        tests.append(
            {
                "name": slug,
                "compose_file": str(UNIT_COMPOSE_FILE.relative_to(ROOT)),
                "compose_project": "tests-unit",
                "compose_service": compose_service,
                "mode": "run",
            }
        )
    return tests


def cmd_list(args: argparse.Namespace) -> int:
    data = load_registry(args.path)
    services = iter_services(data)
    for service in services:
        slug = service.get("name", "<unknown>")
        type_value = service.get("type", "?")
        desc = service.get("description", "").strip()
        path_value = service_path(slug).relative_to(ROOT)
        description = f" — {desc}" if desc else ""
        print(f"- {slug} ({type_value}) -> {path_value}{description}")
    return 0


def cmd_tests(args: argparse.Namespace) -> int:
    data = load_registry(args.path)
    tests = iter_tests(data)
    suite = args.suite
    if suite and suite != "all":
        tests = [test for test in tests if test["name"] == suite]
        if not tests:
            print(f"Unknown test suite: {suite}", file=sys.stderr)
            return 1
    if not tests:
        print("No tests configured in services.yml", file=sys.stderr)
        return 1
    for test in tests:
        print(
            f"{test['name']} {test['compose_project']} {test['compose_file']} "
            f"{test['compose_service']} {test.get('mode', 'run')}"
        )
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    data = load_registry(args.path)
    mapping = gather_log_targets(data)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Services registry helper")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to services.yml (defaults to repository root)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate services.yml structure")
    validate_parser.set_defaults(func=cmd_validate)

    list_parser = subparsers.add_parser("list", help="Print a short summary of services")
    list_parser.set_defaults(func=cmd_list)

    tests_parser = subparsers.add_parser("tests", help="Emit test suites defined in services.yml")
    tests_parser.add_argument("--suite", help="Specific suite to output (default: all)")
    tests_parser.set_defaults(func=cmd_tests)

    logs_parser = subparsers.add_parser("logs", help="Emit mapping for log-capable services")
    logs_parser.add_argument("--service", help="Specific service to query")
    logs_parser.set_defaults(func=cmd_logs)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
