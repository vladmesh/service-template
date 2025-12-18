"""Tests for OpenAPI generator."""

import json

from framework.openapi import generator


def test_generate_openapi(fake_repo) -> None:
    """Test OpenAPI generation from specs."""
    root, _, _, _ = fake_repo

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
""",
        encoding="utf-8",
    )

    # Create service spec
    service_spec_dir = root / "services" / "backend" / "spec"
    service_spec_dir.mkdir(parents=True)

    (service_spec_dir / "users.yaml").write_text(
        """
prefix: /users
tags: [users]
handlers:
  get:
    method: GET
    path: /{id}
    response: {model: User}
""",
        encoding="utf-8",
    )

    # Generate
    output_path = root / "services" / "backend" / "docs" / "openapi.json"
    generator.generate_openapi(root, output_path, service_name="backend")

    assert output_path.exists()

    content = json.loads(output_path.read_text())
    assert content["openapi"] == "3.1.0"
    assert "/users/{id}" in content["paths"]
    assert "User" in content["components"]["schemas"]
