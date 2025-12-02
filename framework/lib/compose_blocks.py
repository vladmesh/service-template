"""Shared helpers for compose block rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

import yaml  # type: ignore[import-untyped]

from framework.lib.env import get_repo_root
from framework.lib.service_scaffold import ServiceSpec

ROOT = get_repo_root()
REGISTRY_PATH = ROOT / "services.yml"
SERVICES_ROOT = ROOT / "services"
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
    ComposeTarget(key="tests_unit", path=ROOT / "infra/compose.tests.unit.yml"),
]


@dataclass(frozen=True)
class ServiceComposeTemplate:
    """String templates for generating compose entries per service."""

    base: str | None = None
    dev: str | None = None
    tests_unit: str | None = None


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
        tests_unit=textwrap.dedent(
            """\
            __SLUG_DASH__-tests-unit:
              image: ${__IMAGE_ENV__:-service-template-__IMAGE_SLUG__:latest}
              build:
                context: ..
                dockerfile: services/__SLUG__/Dockerfile
                args:
                  INSTALL_DEV_DEPS: "true"
              command: >-
                pytest -q --cov=__COV_SOURCE__
                --cov-report=term-missing --cov-fail-under=70
                __UNIT_TEST_TARGET__
              working_dir: /app
              env_file:
                - ../.env
              environment:
                PYTHONPATH: /app
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
              env_file:
                - ../.env
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
        tests_unit=textwrap.dedent(
            """\
            __SLUG_DASH__-tests-unit:
              image: ${__IMAGE_ENV__:-service-template-__IMAGE_SLUG__:latest}
              build:
                context: ..
                dockerfile: services/__SLUG__/Dockerfile
                args:
                  INSTALL_DEV_DEPS: "true"
              command: >-
                pytest -q --cov=__COV_SOURCE__
                --cov-report=term-missing --cov-fail-under=70
                __UNIT_TEST_TARGET__
              working_dir: /app
              env_file:
                - ../.env
              environment:
                PYTHONPATH: /app
                ENVIRONMENT: test
                APP_ENV: test
                DATABASE_URL: sqlite+pysqlite:////app/services/__SLUG__/tests/.tmp/test.db
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
              profiles: ["tg"]
            """
        ),
        tests_unit=DEFAULT_TEMPLATES["python"].tests_unit,
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
    override = SERVICE_OVERRIDES.get(spec.slug)
    default_template = DEFAULT_TEMPLATES.get(spec.service_type)
    if not override:
        return default_template
    if not default_template:
        return override
    return ServiceComposeTemplate(
        base=override.base if override.base is not None else default_template.base,
        dev=override.dev if override.dev is not None else default_template.dev,
        tests_unit=(
            override.tests_unit if override.tests_unit is not None else default_template.tests_unit
        ),
    )


def _unit_test_target(spec: ServiceSpec) -> str:
    service_root = SERVICES_ROOT / spec.slug
    unit_tests_dir = service_root / "tests" / "unit"
    if unit_tests_dir.exists():
        return f"services/{spec.slug}/tests/unit"
    tests_dir = service_root / "tests"
    if tests_dir.exists():
        return f"services/{spec.slug}/tests"
    return f"services/{spec.slug}/tests/unit"


def _cov_source(spec: ServiceSpec) -> str:
    """Return coverage source path for a service."""
    return f"services/{spec.slug}/src"


def _apply_placeholders(template: str, spec: ServiceSpec) -> str:
    image_slug = IMAGE_SLUG_OVERRIDES.get(spec.slug, spec.slug.replace("_", "-"))
    replacements = {
        "__SLUG__": spec.slug,
        "__SLUG_DASH__": spec.slug.replace("_", "-"),
        "__IMAGE_ENV__": f"{spec.slug.upper()}_IMAGE",
        "__INSTALL_DEV_ENV__": f"{spec.slug.upper()}_INSTALL_DEV_DEPS",
        "__IMAGE_SLUG__": image_slug,
        "__UNIT_TEST_TARGET__": _unit_test_target(spec),
        "__COV_SOURCE__": _cov_source(spec),
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
        if key == "dev" and not spec.create_dev_template:
            continue
        snippet = getattr(template, key, None)
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
