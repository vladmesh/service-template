#!/usr/bin/env python3
"""Synchronize docker-compose service blocks from services.yml templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
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


def load_registry(path: Path) -> dict[str, Any]:
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
        compose_cfg = service.get("compose", {})
        if not isinstance(compose_cfg, dict):
            continue
        template_cfg = compose_cfg.get("templates", {})
        if not isinstance(template_cfg, dict):
            continue
        template_path = template_cfg.get(key)
        if not template_path:
            continue
        template_file = (ROOT / template_path).resolve()
        if not template_file.exists():
            raise FileNotFoundError(f"Missing compose template: {template_path}")
        templates.append(template_file)
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


def sync_target(target: ComposeTarget, registry: dict[str, Any]) -> None:
    templates = gather_templates(registry, target.key)
    block_lines = build_service_block(templates, target.indent)
    compose_path = target.path
    lines = compose_path.read_text(encoding="utf-8").splitlines()
    new_lines = replace_block(lines, block_lines)
    compose_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated {compose_path.relative_to(ROOT)} with {len(block_lines)} managed lines")


def main() -> int:
    registry = load_registry(REGISTRY_PATH)
    for target in COMPOSE_TARGETS:
        sync_target(target, registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
