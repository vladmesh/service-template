"""Shared helpers for compose block rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

import yaml

from scripts.lib.env import get_repo_root
from scripts.lib.service_scaffold import ServiceSpec

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


@dataclass(frozen=True)
class ServiceComposeTemplate:
    """String templates for generating compose entries per service."""

    base: str | None = None
    dev: str | None = None


IMAGE_SLUG_OVERRIDES = {
    "tg_bot": "tg",
}


DEFAULT_TEMPLATES: dict[str, ServiceComposeTemplate] = {
    "python": ServiceComposeTemplate(
        base=textwrap.dedent(
            """\
            __SLUG__:
              image: ${__IMAGE_ENV__:-service-template-__IMAGE_SLUG__:latest}
              build:
                context: ..
                dockerfile: services/__SLUG__/Dockerfile
              env_file:
                - ../.env
              networks:
                - internal
            """
        ),
        dev=textwrap.dedent(
            """\
            __SLUG__:
              extends:
                file: compose.base.yml
                service: __SLUG__
              volumes:
                - ../:/workspace:delegated
              working_dir: /workspace
              env_file:
                - ../.env
            """
        ),
    ),
}


SERVICE_OVERRIDES: dict[str, ServiceComposeTemplate] = {
    "backend": ServiceComposeTemplate(
        base=textwrap.dedent(
            """\
            __SLUG__:
              image: ${__IMAGE_ENV__:-service-template-__IMAGE_SLUG__:latest}
              build:
                context: ..
                dockerfile: services/__SLUG__/Dockerfile
                args:
                  INSTALL_DEV_DEPS: ${__INSTALL_DEV_ENV__:-false}
              environment:
                <<: *backend-env
              command: ["services/__SLUG__/scripts/start.sh"]
              depends_on:
                db:
                  condition: service_healthy
              networks:
                - internal
              expose:
                - "8000"
            """
        ),
        dev=textwrap.dedent(
            """\
            __SLUG__:
              extends:
                file: compose.base.yml
                service: __SLUG__
              build:
                context: ..
                dockerfile: services/__SLUG__/Dockerfile
                args:
                  INSTALL_DEV_DEPS: ${__INSTALL_DEV_ENV__:-false}
              command: >-
                bash -lc "./services/__SLUG__/scripts/migrate.sh &&
                uvicorn services.backend.src.main:app --host 0.0.0.0 --port 8000 --reload"
              volumes:
                - ../:/workspace:delegated
              working_dir: /workspace
              env_file:
                - ../.env
              environment:
                PYTHONPATH: /workspace
            """
        ),
    ),
    "tg_bot": ServiceComposeTemplate(
        base=textwrap.dedent(
            """\
            __SLUG__:
              image: ${__IMAGE_ENV__:-service-template-__IMAGE_SLUG__:latest}
              build:
                context: ..
                dockerfile: services/__SLUG__/Dockerfile
              env_file:
                - ../.env
              depends_on:
                backend:
                  condition: service_started
              networks:
                - internal
            """
        ),
    ),
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"services registry not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("services.yml must start with a mapping")
    return data


def compose_template_for_spec(spec: ServiceSpec) -> ServiceComposeTemplate | None:
    if spec.slug in SERVICE_OVERRIDES:
        return SERVICE_OVERRIDES[spec.slug]
    return DEFAULT_TEMPLATES.get(spec.service_type)


def _apply_placeholders(template: str, spec: ServiceSpec) -> str:
    image_slug = IMAGE_SLUG_OVERRIDES.get(spec.slug, spec.slug.replace("_", "-"))
    replacements = {
        "__SLUG__": spec.slug,
        "__SLUG_DASH__": spec.slug.replace("_", "-"),
        "__IMAGE_ENV__": f"{spec.slug.upper()}_IMAGE",
        "__INSTALL_DEV_ENV__": f"{spec.slug.upper()}_INSTALL_DEV_DEPS",
        "__IMAGE_SLUG__": image_slug,
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered.rstrip("\n") + "\n"


def render_service_templates(specs: list[ServiceSpec], key: str) -> list[str]:
    templates: list[str] = []
    for spec in specs:
        template = compose_template_for_spec(spec)
        if not template:
            continue
        snippet = template.base if key == "base" else template.dev
        if key == "dev" and not spec.create_dev_template:
            continue
        if not snippet:
            continue
        templates.append(_apply_placeholders(snippet, spec))
    return templates


def indent_template(text: str, indent: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return ""
    return textwrap.indent(stripped, indent, lambda _line: True)


def build_service_block(templates: list[str], indent: str) -> list[str]:
    if not templates:
        return [f"{indent}# (no managed services)"]

    block_lines: list[str] = []
    for template in templates:
        indented = indent_template(template, indent)
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
