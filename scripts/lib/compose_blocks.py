"""Shared helpers for compose block rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

import yaml

from scripts.lib.env import get_repo_root
from scripts.lib.service_scaffold import service_compose_template_paths

ROOT = get_repo_root()
REGISTRY_PATH = ROOT / "services.yml"
START_MARKER = "# >>> services (auto-generated from services.yml)"
END_MARKER = "# <<< services (auto-generated from services.yml)"


@dataclass
class ComposeTarget:
    """Represents a compose file managed via templates."""

    key: str
    path: Path
    indent: str = "  "


COMPOSE_TARGETS = [
    ComposeTarget(key="base", path=ROOT / "infra/compose.base.yml"),
    ComposeTarget(key="dev", path=ROOT / "infra/compose.dev.yml"),
]


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"services registry not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("services.yml must start with a mapping")
    return data


def gather_templates(registry: dict[str, Any], key: str) -> list[Path]:
    templates: list[Path] = []
    services = registry.get("services", [])
    if not isinstance(services, list):
        raise ValueError("services entry must be a list")
    for service in services:
        if not isinstance(service, dict):
            continue
        slug = service.get("name")
        if not isinstance(slug, str):
            continue
        template_paths = service_compose_template_paths(slug)
        template_path = template_paths.get(key)
        if not template_path or not template_path.exists():
            continue
        templates.append(template_path.resolve())
    return templates


def indent_template(text: str, indent: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return ""
    return textwrap.indent(stripped, indent, lambda _line: True)


def build_service_block(templates: list[Path], indent: str) -> list[str]:
    if not templates:
        return [f"{indent}# (no managed services)"]

    block_lines: list[str] = []
    for template in templates:
        content = template.read_text(encoding="utf-8")
        indented = indent_template(content, indent)
        if indented:
            block_lines.extend(indented.splitlines())
            block_lines.append("")
    if block_lines and block_lines[-1] == "":
        block_lines.pop()
    return block_lines


def replace_block(lines: list[str], new_block: list[str]) -> list[str]:
    start_idx = next((i for i, line in enumerate(lines) if line.strip() == START_MARKER), None)
    end_idx = next((i for i, line in enumerate(lines) if line.strip() == END_MARKER), None)
    if start_idx is None or end_idx is None or start_idx >= end_idx:
        raise RuntimeError("Could not locate compose service markers in file")
    return lines[: start_idx + 1] + new_block + lines[end_idx:]
