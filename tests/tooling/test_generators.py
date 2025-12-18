"""Tests for modular code generators."""

import importlib
from pathlib import Path
import shutil

from framework import generate


def test_generate_all_creates_files(fake_repo) -> None:
    """Test that generate_all creates all expected files."""
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
  UserCreated:
    fields:
      user_id: int
""",
        encoding="utf-8",
    )

    (spec_dir / "events.yaml").write_text(
        """
events:
  UserCreated:
    message: UserCreated
    publish: true
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
  create:
    method: POST
    path: /
    request: {model: User, variant: Create}
    response: {model: User}
""",
        encoding="utf-8",
    )

    # Run generation
    generate.generate_all(root)

    # Check shared generated files
    shared_gen = root / "shared" / "shared" / "generated"
    assert (shared_gen / "schemas.py").exists()
    assert (shared_gen / "events.py").exists()

    # Check content
    schemas = (shared_gen / "schemas.py").read_text()
    assert "class User(BaseModel):" in schemas
    assert "class UserCreate(BaseModel):" in schemas

    assert "class UserCreated(BaseModel):" in schemas

    events = (shared_gen / "events.py").read_text()
    assert "broker = RedisBroker" in events

    # Check service generated files (routers & protocols)
    backend_gen = root / "services" / "backend" / "src" / "generated"
    assert (backend_gen / "protocols.py").exists()
    assert (backend_gen / "routers" / "users.py").exists()

    protocols = (backend_gen / "protocols.py").read_text()
    assert "class UsersControllerProtocol(Protocol):" in protocols
    assert "async def create" in protocols

    router = (backend_gen / "routers" / "users.py").read_text()
    assert "router = APIRouter" in router

    # Check service generated files (controllers)
    # We need to create the service directory first for controllers to be generated?
    # Actually controllers are generated in services/backend/src/controllers
    # But only if the service exists.
    # The generator might skip if dir doesn't exist.

    # Let's create a backend service dir
    backend_src = root / "services" / "backend" / "src"
    (backend_src / "controllers").mkdir(parents=True, exist_ok=True)

    # Run again to generate controllers
    generate.generate_all(root)

    assert (backend_src / "controllers" / "users.py").exists()
    controller = (backend_src / "controllers" / "users.py").read_text()
    assert "class UsersController" in controller
    assert "async def create" in controller
