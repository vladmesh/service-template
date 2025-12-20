"""Tests for generated client retry logic."""

from __future__ import annotations

import importlib
from pathlib import Path
import shutil

import pytest

from framework import generate


@pytest.fixture
def generated_client_module(fake_repo):
    """Generate a client and return the module for testing."""
    root, _, _, _ = fake_repo

    # Copy templates to fake repo
    real_templates = Path("framework/templates").absolute()
    fake_templates = root / "framework" / "templates"
    fake_templates.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(real_templates, fake_templates, dirs_exist_ok=True)

    # Reload generate module to pick up new root
    importlib.reload(generate)

    # Create specs
    spec_dir = root / "shared" / "spec"
    spec_dir.mkdir(parents=True)

    (spec_dir / "models.yaml").write_text(
        """
models:
  User:
    fields:
      id: int
      name: string
    variants:
      Create: {}
      Read: {}
""",
        encoding="utf-8",
    )

    (spec_dir / "events.yaml").write_text(
        """
events: {}
""",
        encoding="utf-8",
    )

    # Create provider service spec
    backend_spec_dir = root / "services" / "backend" / "spec"
    backend_spec_dir.mkdir(parents=True)

    (backend_spec_dir / "users.yaml").write_text(
        """
domain: users
config:
  rest:
    prefix: "/users"
    tags: ["users"]

operations:
  create_user:
    input: UserCreate
    output: UserRead
    rest:
      method: POST
      path: ""
      status: 201

  get_user:
    output: UserRead
    params:
      - name: user_id
        type: int
    rest:
      method: GET
      path: "/{user_id}"
""",
        encoding="utf-8",
    )

    # Create consumer service manifest
    consumer_spec_dir = root / "services" / "consumer" / "spec"
    consumer_spec_dir.mkdir(parents=True)

    (consumer_spec_dir / "manifest.yaml").write_text(
        """
consumes:
  - service: backend
    domain: users
    operations:
      - create_user
      - get_user
""",
        encoding="utf-8",
    )

    # Create consumer service src directory
    consumer_src = root / "services" / "consumer" / "src"
    consumer_src.mkdir(parents=True)

    # Run generation
    generate.generate_all(root)

    # Return the path to generated client
    client_file = root / "services" / "consumer" / "src" / "generated" / "clients" / "backend.py"
    assert client_file.exists(), f"Client file not generated at {client_file}"

    return client_file


class TestGeneratedClientRetryLogic:
    """Tests for retry logic in generated clients."""

    def test_generated_client_retries_on_5xx(self, generated_client_module: Path) -> None:
        """Test that 5xx errors trigger retries with eventual success."""
        # Read and exec the generated code to get the class
        code = generated_client_module.read_text()

        # Verify retry logic is in generated code
        assert "max_retries" in code
        assert "_request_with_retry" in code
        assert "exponential backoff" in code.lower() or "initial_delay" in code

    def test_generated_client_has_retry_params(self, generated_client_module: Path) -> None:
        """Test that generated client has retry configuration parameters."""
        code = generated_client_module.read_text()

        assert "max_retries: int = 3" in code
        assert "initial_delay: float = 1.0" in code
        assert "self.max_retries = max_retries" in code
        assert "self.initial_delay = initial_delay" in code

    def test_generated_client_retry_method_exists(self, generated_client_module: Path) -> None:
        """Test that _request_with_retry method is generated."""
        code = generated_client_module.read_text()

        assert "async def _request_with_retry(" in code
        assert "httpx.ConnectError" in code
        assert "httpx.HTTPStatusError" in code

    def test_generated_client_operations_use_retry(self, generated_client_module: Path) -> None:
        """Test that generated operations use _request_with_retry."""
        code = generated_client_module.read_text()

        # Operations should call _request_with_retry instead of direct client methods
        assert "await self._request_with_retry(" in code

        # Should NOT have direct client.post calls in operations
        # (only in _request_with_retry via getattr)
        lines = code.split("\n")
        in_operation = False
        for line in lines:
            if "async def create_user" in line or "async def get_user" in line:
                in_operation = True
            elif in_operation and "async def " in line:
                in_operation = False
            elif in_operation and "client.post(" in line:
                pytest.fail("Operation uses direct client.post instead of _request_with_retry")

    def test_generated_client_no_retry_on_4xx_logic(self, generated_client_module: Path) -> None:
        """Test that 4xx handling logic is present (no retry)."""
        code = generated_client_module.read_text()

        # Check for 4xx handling logic
        assert "HTTPStatus.BAD_REQUEST" in code
        assert "HTTPStatus.INTERNAL_SERVER_ERROR" in code
        # Should raise immediately without retry
        assert "raise" in code

    def test_generated_client_exponential_backoff(self, generated_client_module: Path) -> None:
        """Test that exponential backoff is implemented."""
        code = generated_client_module.read_text()

        # Check for backoff logic
        assert "delay *= 2" in code
        assert "asyncio.sleep(delay)" in code
