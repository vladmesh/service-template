#!/usr/bin/env python3
"""Interactive helper that scaffolds a new service."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
SERVICES_FILE = ROOT / "services.yml"
TEMPLATES_DIR = ROOT / "templates" / "services"
COMPOSE_TEMPLATES_DIR = ROOT / "infra" / "compose.services"
PLACEHOLDER = "__SERVICE_NAME__"


def prompt(prompt_text: str, default: str | None = None, validator=None) -> str:
    """Prompt for a single-line input with optional default and validator."""

    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{prompt_text}{suffix}: ").strip()
        if not value and default is not None:
            value = default
        if not value:
            print("Please enter a value.")
            continue
        if validator:
            error = validator(value)
            if error:
                print(error)
                continue
        return value


def prompt_bool(prompt_text: str, default: bool = True) -> bool:
    """Prompt for yes/no value."""

    options = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt_text} [{options}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")


def prompt_multiline(prompt_text: str) -> str:
    """Prompt for multi-line input; stop with a single '.' on its own line."""

    print(f"{prompt_text}\nEnter text. Finish with a single '.' on its own line.")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def slug_validator_factory(existing_names: set[str]):
    def _validator(slug: str) -> str | None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", slug):
            return (
                "Slug must start with a letter and contain only lowercase letters, "
                "digits, or underscores."
            )
        if slug in existing_names:
            return f"Service '{slug}' already exists in services.yml."
        return None

    return _validator


def path_validator(path_value: str) -> str | None:
    if Path(path_value).is_absolute():
        return "Path must be relative to the repository root."
    dest = ROOT / path_value
    if dest.exists():
        return f"Path '{path_value}' already exists."
    return None


def load_services() -> dict[str, Any]:
    if not SERVICES_FILE.exists():
        raise FileNotFoundError(f"Cannot find {SERVICES_FILE}")
    with SERVICES_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def save_services(data: dict[str, Any]) -> None:
    with SERVICES_FILE.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def copy_service_template(service_type: str, target_dir: Path, slug: str) -> None:
    source_dir = TEMPLATES_DIR / service_type
    if not source_dir.exists():
        raise FileNotFoundError(f"Template for type '{service_type}' not found ({source_dir})")
    shutil.copytree(source_dir, target_dir)
    for file in target_dir.rglob("*"):
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PLACEHOLDER in text:
            file.write_text(text.replace(PLACEHOLDER, slug), encoding="utf-8")


def write_if_content(path: Path, content: str) -> None:
    if content:
        path.write_text(content.rstrip() + "\n", encoding="utf-8")


def compose_env_var(slug: str) -> str:
    return f"{slug.upper()}_IMAGE"


def generate_compose_templates(
    slug: str,
    compose_service: str,
    service_path: Path,
    create_dev: bool,
) -> dict[str, str]:
    target_dir = COMPOSE_TEMPLATES_DIR / slug
    if target_dir.exists():
        raise FileExistsError(f"Compose templates directory already exists: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=False)
    dockerfile_path = (service_path / "Dockerfile").as_posix()
    base_content = (
        f"{compose_service}:\n"
        f"  image: ${{{compose_env_var(slug)}:-service-template-{slug}:latest}}\n"
        f"  build:\n"
        f"    context: ..\n"
        f"    dockerfile: {dockerfile_path}\n"
        f"  env_file:\n"
        f"    - ../.env\n"
        f"  networks:\n"
        f"    - internal\n"
    )
    base_file = target_dir / "base.yml"
    base_file.write_text(base_content, encoding="utf-8")

    templates = {"base": str(base_file.relative_to(ROOT).as_posix())}

    if create_dev:
        dev_content = (
            f"{compose_service}:\n"
            f"  extends:\n"
            f"    file: compose.base.yml\n"
            f"    service: {compose_service}\n"
            f"  volumes:\n"
            f"    - ../:/workspace:delegated\n"
            f"  working_dir: /workspace\n"
            f"  env_file:\n"
            f"    - ../.env\n"
        )
        dev_file = target_dir / "dev.yml"
        dev_file.write_text(dev_content, encoding="utf-8")
        templates["dev"] = str(dev_file.relative_to(ROOT).as_posix())
    return templates


def prompt_tests() -> list[dict[str, str]]:
    tests: list[dict[str, str]] = []
    while prompt_bool("Add a test suite entry?", default=not tests):
        name = prompt("Test suite name (e.g. backend)", default=f"suite{len(tests) + 1}")
        description = prompt("Test description", default=f"{name} tests")
        compose_file = prompt(
            "Compose file for tests",
            default="infra/compose.tests.unit.yml",
        )
        compose_project = prompt(
            "Compose project name",
            default="tests-unit",
        )
        compose_service = prompt("Compose service to run", default=f"{name}-tests-unit")
        mode = prompt(
            "Run mode ('run' or 'up')",
            default="run",
            validator=lambda value: None
            if value in {"run", "up"}
            else "Mode must be 'run' or 'up'.",
        )
        tests.append(
            {
                "name": name,
                "description": description,
                "compose_file": compose_file,
                "compose_project": compose_project,
                "service": compose_service,
                "mode": mode,
            }
        )
    return tests


def run_subprocess(args: list[str]) -> None:
    subprocess.run(args, check=True, cwd=ROOT)  # noqa: S603


def main() -> int:
    print("=== Add a new service ===")
    services_data = load_services()
    existing_names = {
        service.get("name")
        for service in services_data.get("services", [])
        if isinstance(service, dict)
    }
    slug = prompt(
        "Service slug (e.g. backend_v2)", validator=slug_validator_factory(existing_names)
    )
    display_name = prompt("Display name", default=slug.replace("_", " ").title())
    service_type = prompt(
        "Service type ('python' or 'default')",
        default="python",
        validator=lambda value: None
        if value in {"python", "default"}
        else "Type must be 'python' or 'default'.",
    )
    default_path = f"services/{slug}"
    service_path_str = prompt("Relative path", default_path, validator=path_validator)
    service_path = ROOT / service_path_str
    description = prompt_multiline("Service description")
    compose_service = prompt("Compose service name", default=slug)
    create_dev = prompt_bool("Generate dev overlay template?", default=True)
    include_logs = prompt_bool("Include service in 'make log' command?", default=True)
    tests = prompt_tests()
    readme_content = prompt_multiline("README.md content (leave blank to keep template)")
    agents_content = prompt_multiline("AGENTS.md content (leave blank to keep template)")

    print("-> Copying service template...")
    service_path.parent.mkdir(parents=True, exist_ok=True)
    copy_service_template(service_type, service_path, slug)
    write_if_content(service_path / "README.md", readme_content)
    write_if_content(service_path / "AGENTS.md", agents_content)

    print("-> Generating compose templates...")
    compose_templates = generate_compose_templates(
        slug=slug,
        compose_service=compose_service,
        service_path=Path(service_path_str),
        create_dev=create_dev,
    )

    print("-> Updating services.yml...")
    service_entry = {
        "name": slug,
        "display_name": display_name,
        "type": service_type,
        "path": service_path_str,
        "description": description or f"{display_name} service",
        "compose": {
            "services": {
                "base": compose_service,
                **({"dev": compose_service} if create_dev else {}),
            },
            "templates": compose_templates,
        },
        "logs": [compose_service] if include_logs else [],
        "tests": tests,
        "tags": [service_type],
    }
    services_data.setdefault("services", []).append(service_entry)
    save_services(services_data)

    print("-> Validating registry and syncing compose files...")
    run_subprocess(
        [
            "python",
            "scripts/services_registry.py",
            "validate",
        ]
    )
    run_subprocess(["python", "scripts/compose_sync.py"])

    print("\nService scaffolding complete!")
    print(f"- Path: {service_path_str}")
    print(f"- Compose service: {compose_service}")
    print("Next steps:")
    print("  * Commit the generated files.")
    print("  * Adjust Dockerfile/tests/compose templates as needed.")
    print("  * Run `make tests` to ensure everything passes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
