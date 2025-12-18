"""Tests for framework.spec.loader module."""

from pathlib import Path
import tempfile

import pytest

from framework.spec.loader import (
    SpecValidationError,
    load_specs,
    validate_specs_cli,
)


@pytest.fixture
def temp_repo() -> Path:
    """Create a temporary repo structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create directories
        (root / "shared" / "spec").mkdir(parents=True)
        (root / "services" / "backend" / "spec").mkdir(parents=True)

        yield root


class TestLoadSpecs:
    """Tests for load_specs function."""

    def test_load_valid_specs(self, temp_repo: Path) -> None:
        """Load valid specs successfully."""
        # Write models.yaml
        models_yaml = """
models:
  User:
    fields:
      id:
        type: int
        readonly: true
      name:
        type: string
    variants:
      Create: {}
      Read: {}
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        # Write router
        router_yaml = """
rest:
  prefix: "/users"
  tags: ["users"]

handlers:
  create_user:
    method: POST
    path: /
    request: UserCreate
    response: UserRead
    status: 201
"""
        (temp_repo / "services" / "backend" / "spec" / "users.yaml").write_text(router_yaml)

        specs = load_specs(temp_repo)

        assert "User" in specs.models.models
        assert "backend/users" in specs.routers

    def test_missing_models_yaml(self, temp_repo: Path) -> None:
        """Missing models.yaml should fail."""
        with pytest.raises(SpecValidationError, match="not found"):
            load_specs(temp_repo)

    def test_invalid_yaml_syntax(self, temp_repo: Path) -> None:
        """Invalid YAML syntax should fail."""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text("invalid: yaml: syntax:")

        with pytest.raises(SpecValidationError, match="Invalid YAML"):
            load_specs(temp_repo)

    def test_unknown_model_reference(self, temp_repo: Path) -> None:
        """Reference to unknown model should fail."""
        models_yaml = """
models:
  User:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        router_yaml = """
rest:
  prefix: "/users"
handlers:
  get_user:
    method: GET
    path: /
    response: UnknownModel
"""
        (temp_repo / "services" / "backend" / "spec" / "users.yaml").write_text(router_yaml)

        with pytest.raises(SpecValidationError, match="Unknown response model 'UnknownModel'"):
            load_specs(temp_repo)

    def test_events_optional(self, temp_repo: Path) -> None:
        """Events.yaml is optional."""
        models_yaml = """
models:
  User:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        specs = load_specs(temp_repo)

        assert len(specs.events.events) == 0

    def test_load_events(self, temp_repo: Path) -> None:
        """Load events successfully."""
        models_yaml = """
models:
  UserEvent:
    fields:
      user_id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        events_yaml = """
events:
  user_created:
    message: UserEvent
    publish: true
"""
        (temp_repo / "shared" / "spec" / "events.yaml").write_text(events_yaml)

        specs = load_specs(temp_repo)

        assert len(specs.events.events) == 1
        assert specs.events.events[0].name == "user_created"


class TestValidateSpecsCli:
    """Tests for CLI-friendly validation."""

    def test_valid_specs_pass(self, temp_repo: Path) -> None:
        """Valid specs return success."""
        models_yaml = """
models:
  User:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        success, message = validate_specs_cli(temp_repo)

        assert success is True
        assert "PASSED" in message
        assert "Models: 1" in message

    def test_invalid_specs_fail(self, temp_repo: Path) -> None:
        """Invalid specs return failure."""
        success, message = validate_specs_cli(temp_repo)

        assert success is False
        assert "FAILED" in message
