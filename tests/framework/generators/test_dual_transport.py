from unittest.mock import MagicMock

from framework.generators.routers import RoutersGenerator
from framework.spec.operations import DomainSpec


class TestDualTransport:
    def test_router_generates_publish_on_success(self, tmp_path):
        # 1. Setup specs with dual transport (REST + Events)
        op_spec = {
            "input": "UserCreate",
            "output": "UserRead",
            "rest": {"method": "POST", "status": 201},
            "events": {"publish_on_success": "user.created"},
        }

        domain_data = {
            "config": {"rest": {"prefix": "/users", "tags": ["users"]}},
            "operations": {"create_user": op_spec},
        }

        domain = DomainSpec.from_yaml("users", domain_data)

        specs = MagicMock()
        specs.domains = {"backend/users": domain}

        # 2. Run generator
        generator = RoutersGenerator(specs, tmp_path)
        generated_files = generator.generate()

        assert len(generated_files) == 1
        router_file = generated_files[0]
        content = router_file.read_text()

        # 3. Verify content
        # Check imports
        assert "from faststream.redis import RedisBroker" in content

        # Check create_router signature
        assert "get_broker: Callable[[], RedisBroker]," in content

        # Check handler dependency injection
        assert "broker: RedisBroker = Depends(get_broker)" in content

        # Check publishing logic
        assert 'await broker.publish(result, "user.created")' in content

    def test_router_skips_broker_if_no_events(self, tmp_path):
        # 1. Setup specs with only REST
        op_spec = {
            "output": "UserRead",
            "rest": {"method": "GET", "path": "/{user_id}"},
            "params": [{"name": "user_id", "type": "int"}],
        }

        domain_data = {
            "config": {"rest": {"prefix": "/users"}},
            "operations": {"get_user": op_spec},
        }

        domain = DomainSpec.from_yaml("users", domain_data)

        specs = MagicMock()
        specs.domains = {"backend/users": domain}

        # 2. Run generator
        generator = RoutersGenerator(specs, tmp_path)
        generated_files = generator.generate()

        router_file = generated_files[0]
        content = router_file.read_text()

        # 3. Verify absence of event logic
        assert "from faststream.redis import RedisBroker" not in content
        assert "get_broker" not in content
        assert "broker.publish" not in content
