"""Tests for RegistryGenerator."""

from pathlib import Path
import tempfile

import pytest

from framework.generators.registry import RegistryGenerator
from framework.spec.loader import load_specs


@pytest.fixture
def temp_repo() -> Path:
    """Create a temporary repo structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create directories
        (root / "shared" / "spec").mkdir(parents=True)
        (root / "services" / "backend" / "spec").mkdir(parents=True)
        (root / "services" / "backend" / "src" / "generated" / "routers").mkdir(parents=True)

        yield root


class TestRegistryGenerator:
    """Tests for RegistryGenerator."""

    def test_generates_registry_for_service_with_rest_operations(self, temp_repo: Path) -> None:
        """Generator creates registry.py for services with REST operations."""
        # Setup: models.yaml
        models_yaml = """
models:
  User:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        # Setup: domain spec with REST operations
        domain_yaml = """
domain: users
config:
  rest:
    prefix: "/users"

operations:
  get_user:
    output: User
    params:
      - name: user_id
        type: int
    rest:
      method: GET
      path: "/{user_id}"

  create_user:
    input: User
    output: User
    rest:
      method: POST
      path: ""
"""
        (temp_repo / "services" / "backend" / "spec" / "users.yaml").write_text(domain_yaml)

        # Run generator
        specs = load_specs(temp_repo)
        generator = RegistryGenerator(specs, temp_repo)
        generated = generator.generate()

        # Verify
        assert len(generated) == 1
        output_file = generated[0]
        assert output_file.exists()
        assert "registry.py" in str(output_file)

        content = output_file.read_text()
        assert "create_api_router" in content
        assert "UsersControllerProtocol" in content
        assert "create_users_router" in content
        assert "get_users_controller" in content

    def test_registry_includes_all_domain_routers(self, temp_repo: Path) -> None:
        """Registry includes routers from all domains in a service."""
        models_yaml = """
models:
  User:
    fields:
      id:
        type: int
  Product:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        # Create two domains
        users_yaml = """
domain: users
config:
  rest:
    prefix: "/users"
operations:
  get_user:
    output: User
    rest:
      method: GET
      path: ""
"""
        products_yaml = """
domain: products
config:
  rest:
    prefix: "/products"
operations:
  get_product:
    output: Product
    rest:
      method: GET
      path: ""
"""
        (temp_repo / "services" / "backend" / "spec" / "users.yaml").write_text(users_yaml)
        (temp_repo / "services" / "backend" / "spec" / "products.yaml").write_text(products_yaml)

        specs = load_specs(temp_repo)
        generator = RegistryGenerator(specs, temp_repo)
        generated = generator.generate()

        assert len(generated) == 1
        content = generated[0].read_text()

        # Should include both routers
        assert "create_users_router" in content
        assert "create_products_router" in content
        assert "UsersControllerProtocol" in content
        assert "ProductsControllerProtocol" in content
        assert "get_users_controller" in content
        assert "get_products_controller" in content

    def test_registry_includes_event_adapter_import_when_present(self, temp_repo: Path) -> None:
        """Registry imports event_adapter when service has subscribe operations."""
        models_yaml = """
models:
  TaskPayload:
    fields:
      task_id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        domain_yaml = """
domain: tasks
config:
  rest:
    prefix: "/tasks"
operations:
  list_tasks:
    output: TaskPayload
    rest:
      method: GET
      path: ""

  process_task:
    input: TaskPayload
    events:
      subscribe: task.requested
"""
        (temp_repo / "services" / "backend" / "spec" / "tasks.yaml").write_text(domain_yaml)

        specs = load_specs(temp_repo)
        generator = RegistryGenerator(specs, temp_repo)
        generated = generator.generate()

        assert len(generated) == 1
        content = generated[0].read_text()

        # Should include event_adapter import
        assert "create_event_adapter" in content
        assert "__all__" in content

    def test_no_registry_for_service_without_rest_operations(self, temp_repo: Path) -> None:
        """Services with only events operations don't get registry.py."""
        models_yaml = """
models:
  EventData:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        # Events-only domain (no REST)
        domain_yaml = """
domain: worker
operations:
  process_event:
    input: EventData
    events:
      subscribe: data.received
"""
        (temp_repo / "services" / "backend" / "spec" / "worker.yaml").write_text(domain_yaml)

        specs = load_specs(temp_repo)
        generator = RegistryGenerator(specs, temp_repo)
        generated = generator.generate()

        # No registry generated (no REST operations)
        assert len(generated) == 0

    def test_registry_exports_protocols_in_all(self, temp_repo: Path) -> None:
        """Registry re-exports protocols in __all__ for convenient imports."""
        models_yaml = """
models:
  Item:
    fields:
      id:
        type: int
"""
        (temp_repo / "shared" / "spec" / "models.yaml").write_text(models_yaml)

        domain_yaml = """
domain: items
config:
  rest:
    prefix: "/items"
operations:
  get_item:
    output: Item
    rest:
      method: GET
      path: ""
"""
        (temp_repo / "services" / "backend" / "spec" / "items.yaml").write_text(domain_yaml)

        specs = load_specs(temp_repo)
        generator = RegistryGenerator(specs, temp_repo)
        generated = generator.generate()

        assert len(generated) == 1
        content = generated[0].read_text()

        # Should export in __all__
        assert "__all__" in content
        assert '"create_api_router"' in content
        assert '"ItemsControllerProtocol"' in content
