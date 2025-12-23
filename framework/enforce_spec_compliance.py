"""Enforce spec-driven development by forbidding manual models and routers."""

import ast
from pathlib import Path
import sys

from framework.lib.env import get_repo_root


def is_violation(node: ast.AST, content: str) -> bool:
    """Check if node represents a violation."""
    # Check for Pydantic BaseModel inheritance
    if isinstance(node, ast.ClassDef):
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                return True

    # Check for APIRouter instantiation
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "APIRouter":
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "APIRouter":
            return True

    return False


def check_file(file_path: Path) -> list[tuple[int, str]]:
    """Check a single file for violations."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception as e:
        print(f"Failed to parse {file_path}: {e}")
        return []

    violations = []
    lines = content.splitlines()

    for node in ast.walk(tree):
        if is_violation(node, content):
            # Check for noqa on the same line
            lineno = node.lineno
            if lineno <= len(lines):
                line_content = lines[lineno - 1]
                if "# noqa" in line_content or "#noqa" in line_content:
                    continue

            msg = "Violation found"
            if isinstance(node, ast.ClassDef):
                msg = (
                    f"Defining Pydantic model '{node.name}' manually is forbidden. "
                    "Use shared/spec/models.yaml."
                )
            elif isinstance(node, ast.Call):
                msg = (
                    "Instantiating APIRouter manually is forbidden. Use shared/spec/routers/*.yaml."
                )

            violations.append((node.lineno, msg))

    return violations


def main() -> None:
    """Main entry point."""
    repo_root = get_repo_root()
    services_dir = repo_root / "services"

    if not services_dir.exists():
        print("No services directory found.")
        return

    violations_found = False

    for file_path in services_dir.rglob("*.py"):
        # Skip migrations, tests, and generated code
        if (
            "migrations" in file_path.parts
            or "tests" in file_path.parts
            or "generated" in file_path.parts
        ):
            continue

        # Skip __init__.py files (usually safe)
        if file_path.name == "__init__.py":
            continue

        # Skip wiring layer files - these are allowed to use APIRouter
        # router.py: top-level router composition that includes generated routers
        # health.py: infrastructure health endpoints (not domain logic)
        if file_path.name in ("router.py", "health.py"):
            continue

        file_violations = check_file(file_path)
        if file_violations:
            violations_found = True
            print(f"\nIn {file_path.relative_to(repo_root)}:")
            for lineno, msg in file_violations:
                print(f"  Line {lineno}: {msg}")

    if violations_found:
        print("\nSpec compliance check FAILED.")
        sys.exit(1)
    else:
        print("Spec compliance check PASSED.")


if __name__ == "__main__":
    main()
