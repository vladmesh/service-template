"""Tests for validate_specs module."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def spec_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a minimal repo structure for spec validation tests."""
    root = tmp_path / "repo"
    monkeypatch.setenv("SERVICE_TEMPLATE_ROOT", str(root))

    # Create directory structure
    shared_spec = root / "shared" / "spec"
    shared_spec.mkdir(parents=True, exist_ok=True)

    services_dir = root / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    # Import module after setting env
    import framework.validate_specs as validate_mod

    validate_mod = importlib.reload(validate_mod)

    yield root, validate_mod

    monkeypatch.delenv("SERVICE_TEMPLATE_ROOT", raising=False)


def _write_models(root: Path, content: str) -> None:
    models_file = root / "shared" / "spec" / "models.yaml"
    models_file.write_text(content, encoding="utf-8")


def _write_events(root: Path, content: str) -> None:
    events_file = root / "shared" / "spec" / "events.yaml"
    events_file.write_text(content, encoding="utf-8")


def _write_router(root: Path, service: str, name: str, content: str) -> None:
    spec_dir = root / "services" / service / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / f"{name}.yaml").write_text(content, encoding="utf-8")


class TestValidateModels:
    """Tests for models.yaml validation."""

    def test_valid_models(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
      name:
        type: string
        min_length: 1
        max_length: 100
      is_active:
        type: bool
        default: false
    variants:
      Create:
        exclude: [id]
      Update:
        optional: [name, is_active]
      Read: {}
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert not result.has_errors(), f"Unexpected errors: {result.errors}"

    def test_unknown_type(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  Item:
    fields:
      data:
        type: json
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Unknown type 'json'" in str(e) for e in result.errors)

    def test_valid_list_type(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  Item:
    fields:
      tags:
        type: list[string]
      counts:
        type: list[int]
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert not result.has_errors()

    def test_invalid_list_inner_type(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  Item:
    fields:
      data:
        type: list[json]
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Unknown type 'list[json]'" in str(e) for e in result.errors)

    def test_missing_field_type(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  Item:
    fields:
      name:
        min_length: 1
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("missing 'type'" in str(e) for e in result.errors)

    def test_exclude_nonexistent_field(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
    variants:
      Create:
        exclude: [nonexistent]
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("'nonexistent' does not exist" in str(e) for e in result.errors)

    def test_optional_nonexistent_field(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
    variants:
      Update:
        optional: [missing_field]
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("'missing_field' does not exist" in str(e) for e in result.errors)

    def test_unknown_constraint(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  Item:
    fields:
      name:
        type: string
        pattern: "^[a-z]+$"
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Unknown field constraint 'pattern'" in str(e) for e in result.errors)


class TestValidateRouters:
    """Tests for router spec validation."""

    def test_valid_router(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
      name:
        type: string
    variants:
      Create: {}
      Read: {}
""",
        )
        _write_router(
            root,
            "backend",
            "users",
            """
rest:
  router:
    prefix: "/users"
  handlers:
    create_user:
      method: POST
      path: ""
      request:
        model: User
        variant: Create
      response:
        model: User
        variant: Read
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert not result.has_errors()

    def test_unknown_model(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
""",
        )
        _write_router(
            root,
            "backend",
            "items",
            """
rest:
  handlers:
    get_item:
      method: GET
      path: "/{item_id}"
      response:
        model: Item
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Unknown model 'Item'" in str(e) for e in result.errors)

    def test_unknown_variant(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
    variants:
      Read: {}
""",
        )
        _write_router(
            root,
            "backend",
            "users",
            """
rest:
  handlers:
    update_user:
      method: PUT
      path: "/{user_id}"
      request:
        model: User
        variant: Patch
      response:
        model: User
        variant: Read
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Unknown variant 'Patch'" in str(e) for e in result.errors)

    def test_invalid_http_method(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
""",
        )
        _write_router(
            root,
            "backend",
            "users",
            """
rest:
  handlers:
    get_user:
      method: FETCH
      path: "/{user_id}"
      response:
        model: User
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Invalid HTTP method 'FETCH'" in str(e) for e in result.errors)

    def test_null_response_model_allowed(self, spec_repo):
        """DELETE endpoints often have no response body."""
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
""",
        )
        _write_router(
            root,
            "backend",
            "users",
            """
rest:
  handlers:
    delete_user:
      method: DELETE
      path: "/{user_id}"
      response:
        model: null
        status_code: 204
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert not result.has_errors()


class TestValidateEvents:
    """Tests for events.yaml validation."""

    def test_valid_events(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  UserCreatedEvent:
    fields:
      user_id:
        type: int
      timestamp:
        type: datetime
""",
        )
        _write_events(
            root,
            """
events:
  user_created:
    message: UserCreatedEvent
    publish: true
    subscribe: false
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert not result.has_errors()

    def test_unknown_message_type(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
""",
        )
        _write_events(
            root,
            """
events:
  order_placed:
    message: OrderPlacedEvent
    publish: true
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("Unknown message type 'OrderPlacedEvent'" in str(e) for e in result.errors)

    def test_missing_message_type(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
""",
        )
        _write_events(
            root,
            """
events:
  something_happened:
    publish: true
""",
        )

        result = validate_mod.validate_all_specs(root)
        assert result.has_errors()
        assert any("missing 'message' type" in str(e) for e in result.errors)


class TestIntegration:
    """Integration tests for the full validation pipeline."""

    def test_main_returns_zero_on_valid_specs(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      id:
        type: int
        readonly: true
      name:
        type: string
    variants:
      Create:
        exclude: [id]
      Read: {}
""",
        )

        exit_code = validate_mod.main()
        assert exit_code == 0

    def test_main_returns_one_on_invalid_specs(self, spec_repo):
        root, validate_mod = spec_repo
        _write_models(
            root,
            """
models:
  User:
    fields:
      data:
        type: invalid_type
""",
        )

        exit_code = validate_mod.main()
        assert exit_code == 1
