"""Shared fixtures for copier template tests."""

from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
VENV_COPIER = REPO_ROOT / ".venv" / "bin" / "copier"

BASE_DATA = {
    "project_name": "test-project",
    "project_description": "Test project description",
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "python_version": "3.12",
}


@pytest.fixture(scope="session", autouse=True)
def copier_available():
    """Check if copier is available in the project venv."""
    if not VENV_COPIER.exists():
        pytest.skip(f"copier not found at {VENV_COPIER} (run 'make setup')")


def run_copier(dest: Path, modules: str) -> Path:
    """Run copier copy and return the output directory."""
    output_dir = dest / "output"
    output_dir.mkdir(exist_ok=True)

    cmd = [
        str(VENV_COPIER),
        "copy",
        str(REPO_ROOT),
        str(output_dir),
        "--trust",
        "--defaults",
        "--vcs-ref=HEAD",
        *(f"--data={k}={v}" for k, v in BASE_DATA.items()),
        f"--data=modules={modules}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))  # noqa: S603
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
                    if "{{ project_name }}" in content or "{{ _has_" in content:
                        errors.append(f"Jinja artifact in {file.relative_to(directory)}")
            except UnicodeDecodeError:
                pass

    return errors


@pytest.fixture(scope="session")
def project_backend(tmp_path_factory):
    """Generate a backend-only project (once per session)."""
    return run_copier(tmp_path_factory.mktemp("backend"), "backend")


@pytest.fixture(scope="session")
def project_standalone(tmp_path_factory):
    """Generate a standalone tg_bot project (once per session)."""
    return run_copier(tmp_path_factory.mktemp("standalone"), "tg_bot")


@pytest.fixture(scope="session")
def project_backend_tg_bot(tmp_path_factory):
    """Generate a backend+tg_bot project (once per session)."""
    return run_copier(tmp_path_factory.mktemp("backend_tg_bot"), "backend,tg_bot")


@pytest.fixture(scope="session")
def project_fullstack(tmp_path_factory):
    """Generate a fullstack project (once per session)."""
    return run_copier(tmp_path_factory.mktemp("fullstack"), "backend,tg_bot,notifications,frontend")
