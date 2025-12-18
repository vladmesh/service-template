"""TypeScript type generator from internal specs.

Generates TypeScript interfaces from models.yaml for frontend type safety.
"""

from __future__ import annotations

from pathlib import Path

from framework.lib.env import get_repo_root
from framework.spec.loader import AllSpecs, load_specs
from framework.spec.models import FieldSpec
from framework.spec.types import (
    DictType,
    EnumType,
    ListType,
    OptionalType,
    PrimitiveType,
    TypeSpec,
)


def type_spec_to_typescript(spec: TypeSpec) -> str:
    """Convert TypeSpec to TypeScript type string."""
    if isinstance(spec, PrimitiveType):
        mapping = {
            "int": "number",
            "float": "number",
            "string": "string",
            "bool": "boolean",
            "datetime": "string",  # ISO datetime string
            "uuid": "string",
        }
        return mapping.get(spec.type, "unknown")

    if isinstance(spec, ListType):
        inner = type_spec_to_typescript(spec.of)
        return f"{inner}[]"

    if isinstance(spec, DictType):
        key = type_spec_to_typescript(spec.key)
        value = type_spec_to_typescript(spec.value)
        return f"Record<{key}, {value}>"

    if isinstance(spec, OptionalType):
        inner = type_spec_to_typescript(spec.of)
        return f"{inner} | null"

    if isinstance(spec, EnumType):
        # Return union of string literals
        values = " | ".join(f'"{v}"' for v in spec.values)
        return values

    return "unknown"


def field_to_typescript(field: FieldSpec) -> str:
    """Convert FieldSpec to TypeScript type."""
    return type_spec_to_typescript(field.type_spec)


class TypeScriptGenerator:
    """Generate TypeScript types from validated specs."""

    def __init__(self, specs: AllSpecs) -> None:
        """Initialize with validated specs."""
        self.specs = specs

    def generate(self) -> str:
        """Generate complete TypeScript types file."""
        lines: list[str] = [
            "// Auto-generated TypeScript types from models.yaml",
            "// DO NOT EDIT MANUALLY",
            "",
        ]

        # Generate enums first
        for model_name, model_spec in self.specs.models.models.items():
            for field_name, field_spec in model_spec.fields.items():
                if isinstance(field_spec.type_spec, EnumType):
                    enum_name = f"{model_name}{field_name.title()}"
                    lines.append(self._generate_enum(enum_name, field_spec.type_spec))
                    lines.append("")

        # Generate interfaces
        for model_name, model_spec in self.specs.models.models.items():
            # Base interface
            lines.append(self._generate_interface(model_name, model_spec.fields))
            lines.append("")

            # Variant interfaces
            for variant_name in model_spec.variants:
                variant_full_name = f"{model_name}{variant_name}"
                fields = model_spec.get_variant_fields(variant_name)
                lines.append(self._generate_interface(variant_full_name, fields))
                lines.append("")

        return "\n".join(lines)

    def _generate_enum(self, name: str, spec: EnumType) -> str:
        """Generate TypeScript enum."""
        values = [f'  {v} = "{v}",' for v in spec.values]
        return f"export enum {name} {{\n" + "\n".join(values) + "\n}"

    def _generate_interface(self, name: str, fields: dict[str, FieldSpec]) -> str:
        """Generate TypeScript interface."""
        props = []
        for field_name, field_spec in fields.items():
            ts_type = field_to_typescript(field_spec)
            optional = "?" if field_spec.default is not None else ""
            props.append(f"  {field_name}{optional}: {ts_type};")

        return f"export interface {name} {{\n" + "\n".join(props) + "\n}"


def generate_typescript(
    repo_root: Path | None = None,
    output_path: Path | None = None,
) -> str:
    """Generate TypeScript types and optionally write to file.

    Args:
        repo_root: Repository root path
        output_path: If provided, write to this path

    Returns:
        The generated TypeScript content
    """
    if repo_root is None:
        repo_root = get_repo_root()

    specs = load_specs(repo_root)
    generator = TypeScriptGenerator(specs)
    content = generator.generate()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    return content


def main() -> None:
    """CLI entrypoint for TypeScript generation."""
    repo_root = get_repo_root()
    output_path = repo_root / "frontend" / "generated" / "types.ts"

    # If frontend directory doesn't exist, use shared
    if not (repo_root / "frontend").exists():
        output_path = repo_root / "shared" / "shared" / "generated" / "types.ts"

    generate_typescript(repo_root, output_path)
    print(f"Generated TypeScript types: {output_path}")


if __name__ == "__main__":
    main()
