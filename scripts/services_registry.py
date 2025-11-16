#!/usr/bin/env python3
"""Utility helpers for the services registry (services.yml)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = ROOT / "services.yml"
ALLOWED_TYPES = {"python", "default"}
ALLOWED_TEST_MODES = {"run", "up"}


@dataclass
class ValidationResult:
    """Represents the outcome of registry validation."""

    ok: bool
    errors: list[str]


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Registry file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Registry root must be a mapping")
    return data


def validate_registry(data: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("Registry version must be set to 1")

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

        required_fields = ("display_name", "type", "path", "description")
        for field in required_fields:
            if not isinstance(service.get(field), str) or not service[field]:
                errors.append(f"{prefix}.{field} must be a non-empty string")
        type_value = service.get("type")
        if isinstance(type_value, str) and type_value not in ALLOWED_TYPES:
            errors.append(f"{prefix}.type must be one of {sorted(ALLOWED_TYPES)}")

        path_value = service.get("path")
        if isinstance(path_value, str) and not (ROOT / path_value).exists():
            errors.append(f"{prefix}.path does not exist: {path_value}")

        compose = service.get("compose")
        if not isinstance(compose, dict):
            errors.append(f"{prefix}.compose must be a mapping")
        else:
            svc_map = compose.get("services", {})
            if not isinstance(svc_map, dict):
                errors.append(f"{prefix}.compose.services must be a mapping")

        logs = service.get("logs", [])
        if not isinstance(logs, list):
            errors.append(f"{prefix}.logs must be a list of service names")

        tests = service.get("tests", [])
        if not isinstance(tests, list):
            errors.append(f"{prefix}.tests must be a list")
        else:
            for test in tests:
                if not isinstance(test, dict):
                    errors.append(f"{prefix}.tests entries must be mappings")
                    continue
                for field in ("name", "compose_file", "compose_project", "service"):
                    if not isinstance(test.get(field), str) or not test[field]:
                        errors.append(f"{prefix}.tests.{field} must be a non-empty string")
                        continue
                compose_file = test.get("compose_file")
                if isinstance(compose_file, str) and not (ROOT / compose_file).exists():
                    errors.append(f"{prefix}.tests.compose_file not found: {compose_file}")
                mode = test.get("mode", "run")
                if mode not in ALLOWED_TEST_MODES:
                    errors.append(
                        f"{prefix}.tests.mode must be one of {sorted(ALLOWED_TEST_MODES)}"
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
        name = service.get("name")
        compose_cfg = service.get("compose", {})
        if not isinstance(compose_cfg, dict) or not isinstance(name, str):
            continue
        compose_services = compose_cfg.get("services", {})
        if not isinstance(compose_services, dict):
            continue
        target = compose_services.get("dev") or compose_services.get("base")
        if isinstance(target, str) and target:
            mapping[name] = target
    return mapping


def iter_tests(data: dict[str, Any]) -> list[dict[str, str]]:
    tests: list[dict[str, str]] = []
    for service in iter_services(data):
        entries = service.get("tests", [])
        if not isinstance(entries, list):
            continue
        for test in entries:
            if not isinstance(test, dict):
                continue
            name = test.get("name")
            compose_file = test.get("compose_file")
            compose_project = test.get("compose_project")
            compose_service = test.get("service")
            mode = test.get("mode", "run")
            if not all(
                isinstance(value, str) and value
                for value in (name, compose_file, compose_project, compose_service)
            ):
                continue
            tests.append(
                {
                    "name": name,
                    "compose_file": compose_file,
                    "compose_project": compose_project,
                    "compose_service": compose_service,
                    "mode": mode,
                }
            )
    return tests


def cmd_list(args: argparse.Namespace) -> int:
    data = load_registry(args.path)
    services = iter_services(data)
    for service in services:
        name = service.get("name", "<unknown>")
        display = service.get("display_name", name)
        path_value = service.get("path", "?")
        print(f"- {name} ({display}) -> {path_value}")
    return 0


def cmd_tests(args: argparse.Namespace) -> int:
    data = load_registry(args.path)
    tests = iter_tests(data)
    if args.suite and args.suite != "all":
        tests = [test for test in tests if test["name"] == args.suite]
        if not tests:
            print(f"Unknown test suite: {args.suite}", file=sys.stderr)
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
