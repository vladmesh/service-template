"""Controller-Protocol synchronization checker.

Checks that controller classes implement all methods defined in their protocols.
Can auto-stub missing methods if requested.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from framework.generators.context import OperationContextBuilder
from framework.spec.loader import AllSpecs


@dataclass
class MissingMethod:
    """A method that is missing from a controller."""

    name: str
    params: list[tuple[str, str]]  # [(param_name, param_type), ...]
    return_type: str


@dataclass
class ControllerSyncResult:
    """Result of checking a controller against its protocol."""

    controller_path: Path
    protocol_name: str
    missing_methods: list[MissingMethod]

    @property
    def is_synced(self) -> bool:
        """Check if controller is synchronized with protocol."""
        return len(self.missing_methods) == 0


def get_controller_methods(controller_path: Path) -> set[str]:
    """Extract method names from a controller file using AST."""
    if not controller_path.exists():
        return set()

    try:
        tree = ast.parse(controller_path.read_text())
    except SyntaxError:
        return set()

    methods: set[str] = set()

    for node in ast.walk(tree):
        # Look for async function definitions (our handlers are async)
        if isinstance(node, ast.AsyncFunctionDef):
            methods.add(node.name)
        # Also check regular functions for flexibility
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            methods.add(node.name)

    return methods


def check_controller_sync(
    specs: AllSpecs,
    repo_root: Path,
) -> list[ControllerSyncResult]:
    """Check all controllers against their protocols.

    Returns list of results, one per controller.
    """
    results = []
    context_builder = OperationContextBuilder()

    for domain_key, domain in specs.domains.items():
        service_name, module_name = domain_key.split("/")
        controller_path = (
            repo_root / "services" / service_name / "src" / "controllers" / f"{module_name}.py"
        )

        protocol_name = f"{module_name.capitalize()}ControllerProtocol"

        # Get actual methods from controller
        actual_methods = get_controller_methods(controller_path)

        # Find missing methods with their signatures
        missing = []
        for operation in domain.operations:
            if operation.name not in actual_methods:
                ctx = context_builder.build_for_protocol(operation)

                params = [(p.name, p.type) for p in ctx.params]
                if ctx.input_model:
                    params.append(("data", ctx.input_model))

                missing.append(
                    MissingMethod(
                        name=operation.name,
                        params=params,
                        return_type=ctx.computed_return_type,
                    )
                )

        results.append(
            ControllerSyncResult(
                controller_path=controller_path,
                protocol_name=protocol_name,
                missing_methods=missing,
            )
        )

    return results


def stub_missing_methods(result: ControllerSyncResult) -> None:
    """Add stub methods to a controller for missing protocol methods."""
    if result.is_synced:
        return

    if not result.controller_path.exists():
        # Controller doesn't exist, let generator create it
        return

    content = result.controller_path.read_text()

    # Generate stubs
    stubs = []
    for method in result.missing_methods:
        # Build parameter list
        params_str = "self"
        for name, type_ in method.params:
            params_str += f", {name}: {type_}"

        stub = f'''
    async def {method.name}({params_str}) -> {method.return_type}:
        """TODO: Implement {method.name}."""
        raise NotImplementedError("{method.name} not implemented")
'''
        stubs.append(stub)

    # Find the class definition and append stubs before the end
    # Simple approach: look for the last line and insert before it
    lines = content.rstrip().split("\n")

    # Find the class indentation by looking for "class " line
    class_found = False

    for line in lines:
        if line.strip().startswith("class ") and "Controller" in line:
            class_found = True
            break

    if not class_found:
        # No controller class found, skip
        return

    # Append stubs
    stub_content = "".join(stubs)
    new_content = content.rstrip() + "\n" + stub_content

    result.controller_path.write_text(new_content)


def lint_controllers_cli(repo_root: Path) -> tuple[bool, str]:
    """CLI-friendly controller sync check.

    Returns (success, message).
    """
    from framework.spec.loader import load_specs

    try:
        specs = load_specs(repo_root)
    except Exception as e:  # noqa: BLE001
        return False, f"Failed to load specs: {e}"

    results = check_controller_sync(specs, repo_root)

    all_synced = True
    messages = []

    for result in results:
        if not result.is_synced:
            all_synced = False
            missing_names = [m.name for m in result.missing_methods]
            messages.append(
                f"  {result.controller_path.name}: "
                f"Missing {len(missing_names)} method(s): {', '.join(missing_names)}"
            )

    if all_synced:
        return True, "All controllers are synchronized with their protocols."

    return False, (
        "Controller sync check FAILED.\n"
        + "\n".join(messages)
        + "\n\nRun `make generate-from-spec` to add stubs."
    )
