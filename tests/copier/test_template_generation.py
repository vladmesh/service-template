"""Tests for Copier template generation.

These tests require copier to be installed: pip install copier pyyaml
Run with: pytest tests/copier/ -v
"""

from pathlib import Path
import shutil
import subprocess

import pytest

# Base data for all tests
BASE_DATA = {
    "project_name": "test-project",
    "project_description": "Test project description",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "python_version": "3.12",
}

TEMPLATE_DIR = Path(__file__).parent.parent.parent  # Root of service-template


@pytest.fixture(scope="module")
def copier_available():
    """Check if copier is available."""
    if shutil.which("copier") is None:
        pytest.skip("copier not installed (pip install copier)")


def run_copier(tmp_path: Path, modules: str) -> Path:
    """Run copier copy and return the output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    cmd = [
        "copier",
        "copy",
        str(TEMPLATE_DIR),
        str(output_dir),
        "--trust",
        "--defaults",
        f"--data=project_name={BASE_DATA['project_name']}",
        f"--data=project_description={BASE_DATA['project_description']}",
        f"--data=author_name={BASE_DATA['author_name']}",
        f"--data=author_email={BASE_DATA['author_email']}",
        f"--data=python_version={BASE_DATA['python_version']}",
        f"--data=modules={modules}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=TEMPLATE_DIR)  # noqa: S603
    if result.returncode != 0:
        pytest.fail(f"Copier failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

    return output_dir


def check_no_jinja_artifacts(directory: Path) -> list[str]:
    """Check that no Jinja artifacts remain in generated files."""
    errors = []
    extensions = {".py", ".yml", ".yaml", ".md", ".toml", ".json", ".sh"}

    for file in directory.rglob("*"):
        if file.is_file() and file.suffix in extensions:
            try:
                content = file.read_text()
                if "{{" in content and "{%" in content:
                    # Could be legitimate (e.g., Jinja templates in the project)
                    # Only flag if it looks like unrendered template
                    if "{{ project_name }}" in content or "{{ _has_" in content:
                        errors.append(f"Jinja artifact in {file.relative_to(directory)}")
            except UnicodeDecodeError:
                pass  # Binary file

    return errors


@pytest.mark.usefixtures("copier_available")
class TestBackendOnlyGeneration:
    """Test generation with only backend module."""

    @pytest.fixture
    def generated_project(self, tmp_path: Path) -> Path:
        return run_copier(tmp_path, "backend")

    def test_core_files_exist(self, generated_project: Path):
        """Core files should be generated."""
        assert (generated_project / "Makefile").exists()
        assert (generated_project / "README.md").exists()
        assert (generated_project / "ARCHITECTURE.md").exists()
        assert (generated_project / "CONTRIBUTING.md").exists()
        assert (generated_project / "AGENTS.md").exists()

    def test_services_yml_generated(self, generated_project: Path):
        """services.yml should contain only backend."""
        services_yml = generated_project / "services.yml"
        assert services_yml.exists()

        content = services_yml.read_text()
        assert "backend" in content
        assert "tg_bot" not in content
        assert "notifications_worker" not in content
        assert "frontend" not in content

    def test_backend_service_exists(self, generated_project: Path):
        """Backend service directory should exist."""
        assert (generated_project / "services" / "backend").exists()
        assert (generated_project / "services" / "backend" / "Dockerfile").exists()

    def test_other_services_excluded(self, generated_project: Path):
        """Other service directories should not exist."""
        assert not (generated_project / "services" / "tg_bot").exists()
        assert not (generated_project / "services" / "notifications_worker").exists()
        assert not (generated_project / "services" / "frontend").exists()

    def test_compose_files_valid(self, generated_project: Path):
        """Docker Compose files should be valid YAML."""
        import yaml

        compose_base = generated_project / "infra" / "compose.base.yml"
        assert compose_base.exists()

        content = yaml.safe_load(compose_base.read_text())
        assert "services" in content
        assert "backend" in content["services"]
        assert "db" in content["services"]
        # Redis should not be included for backend-only
        assert "redis" not in content["services"]

    def test_no_jinja_artifacts(self, generated_project: Path):
        """No Jinja template artifacts should remain."""
        errors = check_no_jinja_artifacts(generated_project)
        assert not errors, f"Found Jinja artifacts: {errors}"

    def test_readme_content(self, generated_project: Path):
        """README should contain project info."""
        readme = generated_project / "README.md"
        content = readme.read_text()

        assert BASE_DATA["project_name"] in content
        assert "backend" in content.lower()


@pytest.mark.usefixtures("copier_available")
class TestBackendWithTgBotGeneration:
    """Test generation with backend and tg_bot modules."""

    @pytest.fixture
    def generated_project(self, tmp_path: Path) -> Path:
        return run_copier(tmp_path, "backend,tg_bot")

    def test_both_services_exist(self, generated_project: Path):
        """Both backend and tg_bot should exist."""
        assert (generated_project / "services" / "backend").exists()
        assert (generated_project / "services" / "tg_bot").exists()

    def test_redis_included(self, generated_project: Path):
        """Redis should be included for event-driven modules."""
        import yaml

        compose_base = generated_project / "infra" / "compose.base.yml"
        content = yaml.safe_load(compose_base.read_text())

        assert "redis" in content["services"]

    def test_services_yml_has_both(self, generated_project: Path):
        """services.yml should have both services."""
        content = (generated_project / "services.yml").read_text()
        assert "backend" in content
        assert "tg_bot" in content


@pytest.mark.usefixtures("copier_available")
class TestFullStackGeneration:
    """Test generation with all modules."""

    @pytest.fixture
    def generated_project(self, tmp_path: Path) -> Path:
        return run_copier(tmp_path, "backend,tg_bot,notifications,frontend")

    def test_all_services_exist(self, generated_project: Path):
        """All services should exist."""
        assert (generated_project / "services" / "backend").exists()
        assert (generated_project / "services" / "tg_bot").exists()
        assert (generated_project / "services" / "notifications_worker").exists()
        assert (generated_project / "services" / "frontend").exists()

    def test_no_jinja_artifacts(self, generated_project: Path):
        """No Jinja artifacts in full generation."""
        errors = check_no_jinja_artifacts(generated_project)
        assert not errors, f"Found Jinja artifacts: {errors}"


@pytest.mark.usefixtures("copier_available")
class TestEnvExample:
    """Test .env.example generation."""

    def test_backend_only_env(self, tmp_path: Path):
        """Backend-only should have postgres, no redis."""
        output = run_copier(tmp_path, "backend")
        env_content = (output / ".env.example").read_text()

        assert "POSTGRES" in env_content
        assert "REDIS" not in env_content
        assert "TELEGRAM" not in env_content

    def test_with_tg_bot_env(self, tmp_path: Path):
        """With tg_bot should have redis and telegram."""
        output = run_copier(tmp_path, "backend,tg_bot")
        env_content = (output / ".env.example").read_text()

        assert "POSTGRES" in env_content
        assert "REDIS" in env_content
        assert "TELEGRAM" in env_content


@pytest.mark.usefixtures("copier_available")
class TestModuleExclusion:
    """Test that unselected modules are properly excluded."""

    def test_notifications_excluded_when_not_selected(self, tmp_path: Path):
        """notifications_worker should not exist when not in modules."""
        output = run_copier(tmp_path, "backend,tg_bot")

        assert not (output / "services" / "notifications_worker").exists()
        services_yml = (output / "services.yml").read_text()
        assert "notifications_worker" not in services_yml

    def test_frontend_excluded_when_not_selected(self, tmp_path: Path):
        """frontend should not exist when not in modules."""
        output = run_copier(tmp_path, "backend,notifications")

        assert not (output / "services" / "frontend").exists()
        services_yml = (output / "services.yml").read_text()
        assert "frontend" not in services_yml

    def test_tg_bot_excluded_when_not_selected(self, tmp_path: Path):
        """tg_bot should not exist when not in modules."""
        output = run_copier(tmp_path, "backend,frontend")

        assert not (output / "services" / "tg_bot").exists()
        services_yml = (output / "services.yml").read_text()
        assert "tg_bot" not in services_yml


@pytest.mark.usefixtures("copier_available")
class TestComposeServices:
    """Test Docker Compose service generation."""

    def test_redis_only_with_event_modules(self, tmp_path: Path):
        """Redis should only be included when tg_bot or notifications selected."""
        import yaml

        # Backend only - no redis
        output = run_copier(tmp_path, "backend")
        compose = yaml.safe_load((output / "infra" / "compose.base.yml").read_text())
        assert "redis" not in compose.get("services", {})

    def test_redis_with_notifications(self, tmp_path: Path):
        """Redis should be included with notifications module."""
        import yaml

        output = run_copier(tmp_path, "backend,notifications")
        compose = yaml.safe_load((output / "infra" / "compose.base.yml").read_text())
        assert "redis" in compose["services"]

    def test_all_services_in_compose(self, tmp_path: Path):
        """All selected services should be in compose."""
        import yaml

        output = run_copier(tmp_path, "backend,tg_bot,notifications,frontend")
        compose = yaml.safe_load((output / "infra" / "compose.base.yml").read_text())

        assert "backend" in compose["services"]
        assert "tg_bot" in compose["services"]
        assert "notifications_worker" in compose["services"]
        assert "frontend" in compose["services"]
        assert "redis" in compose["services"]
        assert "db" in compose["services"]
