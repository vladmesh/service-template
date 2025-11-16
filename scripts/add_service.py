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
SERVICES_ROOT = ROOT / "services"
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


def compose_env_var(slug: str) -> str:
    return f"{slug.upper()}_IMAGE"


def generate_compose_templates(
    slug: str,
    service_path: Path,
    create_dev: bool,
) -> None:
    target_dir = COMPOSE_TEMPLATES_DIR / slug
    if target_dir.exists():
        raise FileExistsError(f"Compose templates directory already exists: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=False)
    dockerfile_path = (service_path / "Dockerfile").as_posix()
    base_content = (
        f"{slug}:\n"
        f"  image: ${{{compose_env_var(slug)}:-service-template-{slug}:latest}}\n"
        f"  build:\n"
        f"    context: ..\n"
        f"    dockerfile: {dockerfile_path}\n"
        f"  env_file:\n"
        f"    - ../.env\n"
        f"  networks:\n"
        f"    - internal\n"
    )
    (target_dir / "base.yml").write_text(base_content, encoding="utf-8")

    if create_dev:
        dev_content = (
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
        (target_dir / "dev.yml").write_text(dev_content, encoding="utf-8")


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
    service_type = prompt(
        "Service type ('python' or 'default')",
        default="python",
        validator=lambda value: None
        if value in {"python", "default"}
        else "Type must be 'python' or 'default'.",
    )
    service_path = SERVICES_ROOT / slug
    if service_path.exists():
        raise FileExistsError(f"Service directory already exists: {service_path}")
    description = prompt_multiline("Service description")
    create_dev = prompt_bool("Generate dev overlay template?", default=True)

    print("-> Copying service template...")
    service_path.parent.mkdir(parents=True, exist_ok=True)
    copy_service_template(service_type, service_path, slug)

    print("-> Generating compose templates...")
    generate_compose_templates(
        slug=slug,
        service_path=service_path.relative_to(ROOT),
        create_dev=create_dev,
    )

    print("-> Updating services.yml...")
    services_data.setdefault("version", 2)
    service_entry = {
        "name": slug,
        "type": service_type,
        "description": description or f"{slug.replace('_', ' ').title()} service",
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
    print(f"- Path: {service_path.relative_to(ROOT)}")
    print(f"- Compose service: {slug}")
    print("Next steps:")
    print("  * Commit the generated files.")
    print("  * Adjust Dockerfile/tests/compose templates as needed.")
    print("  * Run `make tests` to ensure everything passes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
