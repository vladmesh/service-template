"""Tests for Copier template generation.

These tests require copier to be installed: pip install copier pyyaml
Run with: pytest tests/copier/ -v
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

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

# Cache for copied template to avoid repeated copies
_template_cache_dir: Path | None = None


def _get_template_dir() -> Path:
    """Get template directory, copying to /tmp if running in Docker with slow mounts."""
    global _template_cache_dir

    if _template_cache_dir is not None and _template_cache_dir.exists():
        return _template_cache_dir

    # Check if we're in a Docker container with mounted workspace (slow I/O)
    # by checking if /workspace exists and is the template dir
    if TEMPLATE_DIR.as_posix().startswith("/workspace"):
        # Copy template to /tmp for faster I/O
        _template_cache_dir = Path(tempfile.mkdtemp(prefix="copier-template-"))
        # Use rsync-like copy excluding heavy/unnecessary dirs
        shutil.copytree(
            TEMPLATE_DIR,
            _template_cache_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "node_modules",
                ".coverage",
            ),
        )
        # Initialize git repo (copier requires it)
        subprocess.run(["git", "init"], cwd=_template_cache_dir, capture_output=True, check=True)  # noqa: S603, S607
        subprocess.run(  # noqa: S603, S607
            ["git", "config", "user.email", "test@test.com"],
            cwd=_template_cache_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(  # noqa: S603, S607
            ["git", "config", "user.name", "Test"],
            cwd=_template_cache_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(  # noqa: S603, S607
            ["git", "add", "."], cwd=_template_cache_dir, capture_output=True, check=True
        )
        subprocess.run(  # noqa: S603, S607
            ["git", "commit", "-m", "init"],
            cwd=_template_cache_dir,
            capture_output=True,
            check=True,
        )
        return _template_cache_dir

    return TEMPLATE_DIR


def run_copier(tmp_path: Path, modules: str) -> Path:
    """Run copier copy and return the output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    template_dir = _get_template_dir()

    cmd = [
        "copier",
        "copy",
        str(template_dir),
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

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=template_dir)  # noqa: S603, S607
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

    def test_product_test_scaffolding(self, generated_project: Path):
        """Product should have test scaffolding, not framework tests."""
        # Product test scaffolding should exist
        tests_dir = generated_project / "tests"
        assert tests_dir.exists(), "tests/ directory should exist"
        assert (tests_dir / "conftest.py").exists(), "tests/conftest.py should exist"
        assert (tests_dir / "integration").exists(), "tests/integration/ should exist"

        # Framework tests should NOT be copied
        assert not (tests_dir / "unit").exists(), "Framework tests/unit/ should not be copied"
        assert not (tests_dir / "copier").exists(), "Framework tests/copier/ should not be copied"
        assert not (tests_dir / "tooling").exists(), "Framework tests/tooling/ should not be copied"

        # conftest.py should not have .jinja extension and should be rendered
        conftest_content = (tests_dir / "conftest.py").read_text()
        assert "{{ project_name }}" not in conftest_content, "Jinja artifacts in conftest.py"
        assert "test-project" in conftest_content or "Pytest configuration" in conftest_content


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

    def test_tg_bot_depends_on_redis(self, generated_project: Path):
        """tg_bot should depend on redis: service_healthy in services.yml."""
        import yaml

        services_yml = generated_project / "services.yml"
        content = yaml.safe_load(services_yml.read_text())

        tg_bot_service = next((s for s in content["services"] if s["name"] == "tg_bot"), None)
        assert tg_bot_service is not None, "tg_bot service not found"
        assert "depends_on" in tg_bot_service
        assert tg_bot_service["depends_on"].get("redis") == "service_healthy"


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
        """Backend-only should have postgres and redis (for events)."""
        output = run_copier(tmp_path, "backend")
        env_content = (output / ".env.example").read_text()

        assert "POSTGRES" in env_content
        # Backend uses events for debug endpoint, so REDIS is included
        assert "REDIS" in env_content
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

    def test_dev_compose_has_event_services(self, tmp_path: Path):
        """compose.dev.yml should include tg_bot, notifications, and redis when selected."""
        import yaml

        output = run_copier(tmp_path, "backend,tg_bot,notifications")
        compose_dev = yaml.safe_load((output / "infra" / "compose.dev.yml").read_text())

        assert "tg_bot" in compose_dev["services"]
        assert "notifications_worker" in compose_dev["services"]
        assert "redis" in compose_dev["services"]

    def test_dev_compose_no_redis_backend_only(self, tmp_path: Path):
        """compose.dev.yml should not include redis for backend-only."""
        import yaml

        output = run_copier(tmp_path, "backend")
        compose_dev = yaml.safe_load((output / "infra" / "compose.dev.yml").read_text())

        assert "redis" not in compose_dev.get("services", {})
        assert "tg_bot" not in compose_dev.get("services", {})


@pytest.mark.usefixtures("copier_available")
class TestIntegration:
    """Integration tests - validate generated project structure."""

    def test_docker_compose_config_valid(self, tmp_path: Path):
        """docker compose config should pass on generated project."""
        if shutil.which("docker") is None:
            pytest.skip("docker not available")

        output = run_copier(tmp_path, "backend")

        result = subprocess.run(  # noqa: S603, S607
            ["docker", "compose", "-f", "infra/compose.base.yml", "config"],
            capture_output=True,
            text=True,
            cwd=output,
        )
        assert result.returncode == 0, f"docker compose config failed: {result.stderr}"

    def test_docker_compose_config_full_stack(self, tmp_path: Path):
        """docker compose config should pass for full stack."""
        if shutil.which("docker") is None:
            pytest.skip("docker not available")

        output = run_copier(tmp_path, "backend,tg_bot,notifications,frontend")

        result = subprocess.run(  # noqa: S603, S607
            ["docker", "compose", "-f", "infra/compose.base.yml", "config"],
            capture_output=True,
            text=True,
            cwd=output,
        )
        assert result.returncode == 0, f"docker compose config failed: {result.stderr}"

    def test_framework_generate_runs(self, tmp_path: Path):
        """framework generation should run successfully via python."""
        # We simulate what 'make generate-from-spec' does inside the container
        # i.e. python -m framework.generate with PYTHONPATH=.framework

        generated_project = run_copier(tmp_path, "backend")

        framework_path = generated_project / ".framework"
        env = {"PYTHONPATH": str(framework_path)}

        # We need to run this using the Current python environment (which has dependencies)
        # But we need to ensure the imports work.
        # The current process is pytest in tooling.

        # Note: We use the generated_project fixture which already ran copier.
        # But generated_project path is inside /tmp (or cache).

        result = subprocess.run(
            [sys.executable, "-m", "framework.generate"],
            cwd=generated_project,  # run from project root
            env={**os.environ, **env},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"framework.generate failed:\nstderr: {result.stderr}\nstdout: {result.stdout}"
        )

    def test_makefile_has_correct_targets(self, tmp_path: Path):
        """Makefile should have expected targets."""
        output = run_copier(tmp_path, "backend")
        makefile = (output / "Makefile").read_text()

        # Core targets should exist
        assert "dev-start:" in makefile
        assert "dev-stop:" in makefile
        assert "lint:" in makefile
        assert "tests:" in makefile
        assert "makemigrations:" in makefile  # backend selected

    def test_makefile_no_migrations_without_backend(self, tmp_path: Path):
        """Makefile should not have makemigrations if no backend."""
        # This test only makes sense if we support non-backend configs
        # For now, just verify backend includes it
        output = run_copier(tmp_path, "backend")
        makefile = (output / "Makefile").read_text()
        assert "makemigrations:" in makefile

    def test_architecture_md_conditional_content(self, tmp_path: Path):
        """ARCHITECTURE.md should have conditional content based on modules."""
        # Backend only - no Redis
        output = run_copier(tmp_path, "backend")
        arch = (output / "ARCHITECTURE.md").read_text()
        assert "PostgreSQL" in arch
        assert "python-fastapi" in arch

    def test_architecture_md_with_events(self, tmp_path: Path):
        """ARCHITECTURE.md should mention Redis when event modules selected."""
        output = run_copier(tmp_path, "backend,tg_bot")
        arch = (output / "ARCHITECTURE.md").read_text()
        assert "Redis" in arch
        assert "python-faststream" in arch

    def test_agents_md_conditional_content(self, tmp_path: Path):
        """AGENTS.md should have conditional content based on modules."""
        output = run_copier(tmp_path, "backend")
        agents = (output / "AGENTS.md").read_text()
        assert "Backend:" in agents
        assert "Telegram Bot:" not in agents

    def test_agents_md_with_tg_bot(self, tmp_path: Path):
        """AGENTS.md should include tg_bot section when selected."""
        output = run_copier(tmp_path, "backend,tg_bot")
        agents = (output / "AGENTS.md").read_text()
        assert "Backend:" in agents
        assert "Telegram Bot:" in agents
        assert "FastStream Event Architecture" in agents


def _init_git_repo(path: Path) -> None:
    """Initialize a git repo in the given path for copier update tests."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)  # noqa: S603, S607
    subprocess.run(  # noqa: S603, S607
        ["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(  # noqa: S603, S607
        ["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)  # noqa: S603, S607
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)  # noqa: S603, S607


@pytest.mark.usefixtures("copier_available")
class TestCopierUpdate:
    """Tests for copier update functionality."""

    def test_update_preserves_user_code(self, tmp_path: Path):
        """copier update should preserve user-created files in protected dirs."""
        output = run_copier(tmp_path, "backend")
        _init_git_repo(output)

        # Create "user" code in protected directory
        user_controller = output / "services" / "backend" / "src" / "controllers" / "custom.py"
        user_controller.parent.mkdir(parents=True, exist_ok=True)
        user_controller.write_text(
            "# My custom controller code\nclass CustomController:\n    pass\n"
        )

        # Commit user changes
        subprocess.run(["git", "add", "."], cwd=output, capture_output=True, check=True)  # noqa: S603, S607
        subprocess.run(  # noqa: S603, S607
            ["git", "commit", "-m", "user code"], cwd=output, capture_output=True, check=True
        )

        # Run copier update
        result = subprocess.run(  # noqa: S603, S607
            [
                "copier",
                "update",
                "--trust",
                "--defaults",
            ],
            capture_output=True,
            text=True,
            cwd=output,
        )
        assert result.returncode == 0, f"copier update failed: {result.stderr}"

        # Verify user code preserved
        assert user_controller.exists(), "User controller was deleted"
        content = user_controller.read_text()
        assert "My custom controller code" in content

    def test_update_preserves_env_example(self, tmp_path: Path):
        """copier update should not overwrite .env.example."""
        output = run_copier(tmp_path, "backend")
        _init_git_repo(output)

        # Modify .env.example
        env_example = output / ".env.example"
        original_content = env_example.read_text()
        modified_content = original_content + "\n# User custom variable\nMY_CUSTOM_VAR=value\n"
        env_example.write_text(modified_content)

        # Commit user changes
        subprocess.run(["git", "add", "."], cwd=output, capture_output=True, check=True)  # noqa: S603, S607
        subprocess.run(  # noqa: S603, S607
            ["git", "commit", "-m", "user env"], cwd=output, capture_output=True, check=True
        )

        # Run copier update
        result = subprocess.run(  # noqa: S603, S607
            [
                "copier",
                "update",
                "--trust",
                "--defaults",
            ],
            capture_output=True,
            text=True,
            cwd=output,
        )
        assert result.returncode == 0, f"copier update failed: {result.stderr}"

        # Verify modification preserved
        content = env_example.read_text()
        assert "MY_CUSTOM_VAR" in content

    def test_update_preserves_spec_files(self, tmp_path: Path):
        """copier update should not overwrite spec files."""
        output = run_copier(tmp_path, "backend")
        _init_git_repo(output)

        # Modify models.yaml
        models_spec = output / "shared" / "spec" / "models.yaml"
        if models_spec.exists():
            original_content = models_spec.read_text()
            modified_content = original_content + "\n# User added model\n"
            models_spec.write_text(modified_content)

            # Commit user changes
            subprocess.run(["git", "add", "."], cwd=output, capture_output=True, check=True)  # noqa: S603, S607
            subprocess.run(  # noqa: S603, S607
                ["git", "commit", "-m", "user spec"], cwd=output, capture_output=True, check=True
            )

            # Run copier update
            result = subprocess.run(  # noqa: S603, S607
                [
                    "copier",
                    "update",
                    "--trust",
                    "--defaults",
                ],
                capture_output=True,
                text=True,
                cwd=output,
            )
            assert result.returncode == 0, f"copier update failed: {result.stderr}"

            # Verify modification preserved
            content = models_spec.read_text()
            assert "User added model" in content

    def test_copier_answers_file_created(self, tmp_path: Path):
        """Generated project should have .copier-answers.yml."""
        output = run_copier(tmp_path, "backend")
        answers_file = output / ".copier-answers.yml"
        assert answers_file.exists(), f"Answers file not found. Contents: {list(output.iterdir())}"

        import yaml

        answers = yaml.safe_load(answers_file.read_text())
        assert answers["project_name"] == "test-project"
        assert answers["modules"] == "backend"


@pytest.mark.usefixtures("copier_available")
class TestWorkflowGeneration:
    """Tests for GitHub Actions workflow generation."""

    def test_workflows_exist(self, tmp_path: Path):
        """GitHub workflows should be generated."""
        output = run_copier(tmp_path, "backend")
        workflows_dir = output / ".github" / "workflows"

        assert workflows_dir.exists()
        assert (workflows_dir / "main.yml").exists()
        assert (workflows_dir / "ci.yml").exists()

    def test_workflow_no_jinja_source_files(self, tmp_path: Path):
        """Jinja source templates should not be copied."""
        output = run_copier(tmp_path, "backend")
        workflows_dir = output / ".github" / "workflows"

        assert not (workflows_dir / "main.yml.jinja").exists()
        assert not (workflows_dir / "ci.yml.jinja").exists()
        assert not (workflows_dir / "test-template.yml").exists()

    def test_backend_only_workflow_matrix(self, tmp_path: Path):
        """Backend-only should have only backend in CI matrix."""
        output = run_copier(tmp_path, "backend")
        main_yml = (output / ".github" / "workflows" / "main.yml").read_text()

        assert "id: backend" in main_yml
        assert "id: tg-bot" not in main_yml
        assert "id: frontend" not in main_yml
        assert "id: notifications-worker" not in main_yml

    def test_full_stack_workflow_matrix(self, tmp_path: Path):
        """Full stack should have all services in CI matrix."""
        output = run_copier(tmp_path, "backend,tg_bot,notifications,frontend")
        main_yml = (output / ".github" / "workflows" / "main.yml").read_text()

        assert "id: backend" in main_yml
        assert "id: tg-bot" in main_yml
        assert "id: frontend" in main_yml
        assert "id: notifications-worker" in main_yml

    def test_partial_modules_workflow_matrix(self, tmp_path: Path):
        """Partial module selection should reflect in CI matrix."""
        output = run_copier(tmp_path, "backend,tg_bot")
        main_yml = (output / ".github" / "workflows" / "main.yml").read_text()

        assert "id: backend" in main_yml
        assert "id: tg-bot" in main_yml
        assert "id: frontend" not in main_yml
        assert "id: notifications-worker" not in main_yml

    def test_workflow_valid_yaml(self, tmp_path: Path):
        """Generated workflows should be valid YAML."""
        import yaml

        output = run_copier(tmp_path, "backend,tg_bot,notifications,frontend")
        workflows_dir = output / ".github" / "workflows"

        for workflow_file in ["main.yml", "ci.yml"]:
            content = yaml.safe_load((workflows_dir / workflow_file).read_text())
            assert "name" in content
            # YAML parses "on" as boolean True, so check for True key
            assert True in content or "on" in content
            assert "jobs" in content

    def test_workflow_no_jinja_artifacts(self, tmp_path: Path):
        """Workflows should not have unrendered Jinja artifacts."""
        output = run_copier(tmp_path, "backend")
        workflows_dir = output / ".github" / "workflows"

        for workflow_file in ["main.yml", "ci.yml"]:
            content = (workflows_dir / workflow_file).read_text()
            # Check for unrendered Jinja (but allow GitHub Actions ${{ }})
            assert "{% if" not in content
            assert "{% endif" not in content
            assert "{{ modules" not in content
            assert "{{ project_" not in content
