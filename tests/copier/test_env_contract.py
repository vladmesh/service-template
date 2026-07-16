"""Tests for generated typed environment contract fragments."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
SCHEMA = json.loads((REPO_ROOT / "tests/fixtures/env-contract.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def env_keys(path: Path) -> set[str]:
    """Return documented variables, excluding comments and blank lines."""
    return {
        line.partition("=")[0]
        for line in path.read_text().splitlines()
        if line and not line.startswith("#")
    }


def fragments(project: Path) -> list[tuple[Path, dict[str, object]]]:
    """Load every generated environment contract fragment."""
    return [
        (path, yaml.safe_load(path.read_text()))
        for path in sorted(project.rglob("env.contract.yaml"))
    ]


@pytest.mark.parametrize(
    "fixture_name",
    [
        "project_backend",
        "project_standalone",
        "project_notifications",
        "project_frontend",
        "project_backend_tg_bot",
        "project_fullstack",
    ],
)
def test_env_contract_fragments_match_vendored_schema(
    request: pytest.FixtureRequest, fixture_name: str
) -> None:
    """Every generated fragment validates without reaching the codegen repository."""
    project = request.getfixturevalue(fixture_name)

    for path, fragment in fragments(project):
        errors = sorted(VALIDATOR.iter_errors(fragment), key=str)
        assert not errors, f"{path.relative_to(project)}: {errors[0].message}"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "project_backend",
        "project_standalone",
        "project_notifications",
        "project_frontend",
        "project_backend_tg_bot",
        "project_fullstack",
    ],
)
def test_env_contract_covers_env_example(
    request: pytest.FixtureRequest, fixture_name: str
) -> None:
    """All documented generated-project variables have one typed declaration."""
    project = request.getfixturevalue(fixture_name)
    declared: dict[str, dict[str, object]] = {}

    for path, fragment in fragments(project):
        for key, entry in fragment["entries"].items():
            assert key not in declared, f"{key} is declared twice, including {path}"
            declared[key] = entry

    assert env_keys(project / ".env.example") == set(declared)


def test_backend_contract_classifies_infrastructure_values(project_backend: Path) -> None:
    """Baseline types distinguish allocations, generated credentials and local ports."""
    entries = {
        key: entry
        for _, fragment in fragments(project_backend)
        for key, entry in fragment["entries"].items()
    }

    assert entries["BACKEND_PORT"]["source"] == "allocation"
    assert entries["BACKEND_PORT"]["service"] == "backend"
    assert entries["POSTGRES_HOST_PORT"] == {
        "source": "literal",
        "environments": ["local"],
        "required": True,
        "value": 5432,
    }
    assert entries["REDIS_HOST_PORT"] == {
        "source": "literal",
        "environments": ["local"],
        "required": True,
        "value": 6379,
    }
    for key in ("APP_SECRET_KEY", "POSTGRES_PASSWORD"):
        assert entries[key]["source"] == "generated_secret"
    assert entries["REDIS_URL"] == {
        "source": "literal",
        "environments": ["local", "production"],
        "consumers": ["backend"],
        "required": True,
        "value": "redis://redis:6379",
    }
    assert entries["APP_ENV"]["source"] == "derived"
    assert entries["BACKEND_IMAGE"]["source"] == "derived"
