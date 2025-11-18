"""Generate Pydantic schemas and FastAPI routers from YAML specifications."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

from scripts.lib.env import get_repo_root


def load_yaml(file_path: Path) -> dict[str, Any]:
    """Load and parse YAML file."""
    with file_path.open() as f:
        return yaml.safe_load(f)


def python_type_from_spec(field_type: str) -> str:
    """Map spec type to Python/Pydantic type."""
    type_mapping = {
        "string": "str",
        "int": "int",
        "bool": "bool",
        "uuid": "UUID",
        "datetime": "datetime",
        "float": "float",
    }
    return type_mapping.get(field_type, field_type)


def get_field_imports(fields: dict[str, Any]) -> set[str]:
    """Determine required imports for fields."""
    imports = set()
    for field_def in fields.values():
        field_type = field_def.get("type", "")
        if field_type == "uuid":
            imports.add("from uuid import UUID")
        elif field_type == "datetime":
            imports.add("from datetime import datetime")
    return imports


def generate_field_definition(
    field_name: str,
    python_type: str,
    field_def: dict[str, Any],
    is_optional: bool = False,
) -> str:
    """Generate field definition with validations and defaults."""
    default = field_def.get("default")
    readonly = field_def.get("readonly", False)

    # Collect validation constraints
    validations = []
    for constraint in ["ge", "gt", "le", "lt", "min_length", "max_length"]:
        if constraint in field_def:
            value = field_def[constraint]
            validations.append(f"{constraint}={value}")

    # Handle optional fields
    if is_optional:
        if validations:
            # For optional fields with validations, we need to handle None
            # Pydantic allows validations on Optional fields
            field_type = f"Optional[{python_type}]"
            validation_str = ", ".join(validations)
            return f"    {field_name}: {field_type} = Field(default=None, {validation_str})"
        else:
            return f"    {field_name}: Optional[{python_type}] = None"

    # Handle default values
    if default is not None:
        if isinstance(default, str):
            default_str = f'"{default}"'
        elif isinstance(default, bool):
            default_str = "True" if default else "False"
        else:
            default_str = str(default)

        if validations:
            validation_str = ", ".join(validations)
            return (
                f"    {field_name}: {python_type} = Field(default={default_str}, {validation_str})"
            )
        else:
            return f"    {field_name}: {python_type} = Field(default={default_str})"

    # Handle readonly fields
    if readonly:
        if validations:
            validation_str = ", ".join(validations)
            return f"    {field_name}: {python_type} = Field(..., {validation_str})"
        else:
            return f"    {field_name}: {python_type} = Field(...)"

    # Required field with or without validations
    if validations:
        validation_str = ", ".join(validations)
        return f"    {field_name}: {python_type} = Field(..., {validation_str})"
    else:
        return f"    {field_name}: {python_type}"


def generate_base_model(model_name: str, fields: dict[str, Any]) -> str:
    """Generate base Pydantic model class."""
    lines = [f"class {model_name}(BaseModel):"]
    lines.append(f'    """Base model for {model_name}."""')
    lines.append("")

    for field_name, field_def in sorted(fields.items()):
        field_type = field_def.get("type", "string")
        python_type = python_type_from_spec(field_type)
        lines.append(generate_field_definition(field_name, python_type, field_def))

    lines.append("")
    lines.append("    class Config:")
    lines.append("        orm_mode = True")
    lines.append("")

    return "\n".join(lines)


def generate_variant_model(
    model_name: str, variant_name: str, base_fields: dict[str, Any], variant_def: dict[str, Any]
) -> str:
    """Generate variant Pydantic model."""
    variant_class_name = f"{model_name}{variant_name}"
    exclude_fields = set(variant_def.get("exclude", []))
    optional_fields = set(variant_def.get("optional", []))

    # If variant is empty (no exclude, no optional), inherit from base model
    if not exclude_fields and not optional_fields:
        lines = [f"class {variant_class_name}({model_name}):"]
        lines.append(f'    """Variant {variant_name} for {model_name}."""')
        lines.append("")
        lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    # If we have exclude fields, create model without inheritance to properly exclude fields
    # Otherwise inherit and override optional fields
    if exclude_fields:
        # Create model without inheritance, only with non-excluded fields
        lines = [f"class {variant_class_name}(BaseModel):"]
        lines.append(f'    """Variant {variant_name} for {model_name}."""')
        lines.append("")

        for field_name, field_def in sorted(base_fields.items()):
            if field_name in exclude_fields:
                continue

            field_type = field_def.get("type", "string")
            python_type = python_type_from_spec(field_type)
            is_optional = field_name in optional_fields
            lines.append(generate_field_definition(field_name, python_type, field_def, is_optional))

        lines.append("")
        lines.append("    class Config:")
        lines.append("        orm_mode = True")
        lines.append("")

        return "\n".join(lines)
    else:
        # Only optional fields, inherit from base and override
        lines = [f"class {variant_class_name}({model_name}):"]
        lines.append(f'    """Variant {variant_name} for {model_name}."""')
        lines.append("")

        for field_name, field_def in sorted(base_fields.items()):
            if field_name not in optional_fields:
                continue

            field_type = field_def.get("type", "string")
            python_type = python_type_from_spec(field_type)
            lines.append(
                generate_field_definition(field_name, python_type, field_def, is_optional=True)
            )

        lines.append("")
        lines.append("    class Config:")
        lines.append("        orm_mode = True")
        lines.append("")

        return "\n".join(lines)


def generate_schemas(models_spec: dict[str, Any]) -> str:
    """Generate schemas.py content from models.yaml."""
    lines = [
        "# AUTO-GENERATED FROM shared/spec/models.yaml – DO NOT EDIT MANUALLY",
        "",
        "from __future__ import annotations",
        "",
        "from typing import Optional",
        "",
        "from pydantic import BaseModel, Field",
        "",
    ]

    models = models_spec.get("models", {})
    all_imports = set()

    for model_name in sorted(models.keys()):
        model_def = models[model_name]
        fields = model_def.get("fields", {})
        all_imports.update(get_field_imports(fields))

    if all_imports:
        # Sort imports: standard library first, then third-party
        stdlib_imports = [imp for imp in sorted(all_imports) if imp.startswith("from datetime")]
        other_imports = [imp for imp in sorted(all_imports) if not imp.startswith("from datetime")]
        if stdlib_imports:
            lines.extend(stdlib_imports)
        if other_imports:
            lines.extend(other_imports)
        if all_imports:
            lines.append("")

    for model_name in sorted(models.keys()):
        model_def = models[model_name]
        fields = model_def.get("fields", {})
        variants = model_def.get("variants", {})

        lines.append(generate_base_model(model_name, fields))

        for variant_name in sorted(variants.keys()):
            variant_def = variants[variant_name]
            lines.append(generate_variant_model(model_name, variant_name, fields, variant_def))

    return "\n".join(lines)


def extract_path_params(path: str) -> list[tuple[str, str]]:
    """Extract path parameters from route path. Returns list of (param_name, param_type)."""
    pattern = r"\{(\w+)\}"
    matches = re.findall(pattern, path)
    return [(match, "int") for match in matches]


def get_response_model(response_def: dict[str, Any] | None, models: dict[str, Any]) -> str | None:
    """Get response model class name from response definition."""
    if not response_def:
        return None

    model_name = response_def.get("model")
    if not model_name:
        return None

    variant_name = response_def.get("variant")
    if variant_name:
        return f"{model_name}{variant_name}"
    return model_name


def get_request_model(request_def: dict[str, Any] | None, models: dict[str, Any]) -> str | None:
    """Get request model class name from request definition."""
    if not request_def:
        return None

    model_name = request_def.get("model")
    if not model_name:
        return None

    variant_name = request_def.get("variant")
    if variant_name:
        return f"{model_name}{variant_name}"
    return model_name


def generate_router(rest_spec: dict[str, Any], models_spec: dict[str, Any]) -> str:
    """Generate routers/rest.py content from rest.yaml."""
    lines = [
        "# AUTO-GENERATED FROM shared/spec/rest.yaml – DO NOT EDIT MANUALLY",
        "",
        "from __future__ import annotations",
        "",
        "from typing import List",
        "",
        "from fastapi import APIRouter",
        "",
    ]

    rest = rest_spec.get("rest", {})
    router_config = rest.get("router", {})
    handlers = rest.get("handlers", {})

    models = models_spec.get("models", {})

    prefix = router_config.get("prefix", "")
    tags = router_config.get("tags", [])
    async_handlers = router_config.get("async_handlers", True)

    router_params = []
    if prefix:
        router_params.append(f'prefix="{prefix}"')
    if tags:
        tags_str = str(tags)
        router_params.append(f"tags={tags_str}")

    router_line = "router = APIRouter(" + ", ".join(router_params) + ")"
    lines.append(router_line)
    lines.append("")

    imports_needed = set()

    for handler_name in sorted(handlers.keys()):
        handler_def = handlers[handler_name]
        method = handler_def.get("method", "GET").lower()
        path = handler_def.get("path", "/")
        request_def = handler_def.get("request")
        response_def = handler_def.get("response", {})

        path_params = extract_path_params(path)
        request_model = get_request_model(request_def, models)
        response_model = get_response_model(response_def, models)

        if request_model:
            imports_needed.add(request_model)
        if response_model:
            imports_needed.add(response_model)

    if imports_needed:
        imports_line = "from shared.generated.schemas import " + ", ".join(sorted(imports_needed))
        # Insert after fastapi import
        lines.insert(7, imports_line)
        lines.insert(8, "")

    for handler_name in sorted(handlers.keys()):
        handler_def = handlers[handler_name]
        method = handler_def.get("method", "GET").lower()
        path = handler_def.get("path", "/")
        request_def = handler_def.get("request")
        response_def = handler_def.get("response", {})

        path_params = extract_path_params(path)
        request_model = get_request_model(request_def, models)
        response_model = get_response_model(response_def, models)
        many = response_def.get("many", False) if response_def else False
        status_code = response_def.get("status_code") if response_def else None
        handler_tags = handler_def.get("tags")

        if status_code is None:
            if method == "post":
                status_code = 201
            else:
                status_code = 200

        decorator_params = [f'"{path}"']
        if response_model:
            if many:
                response_type = f"List[{response_model}]"
            else:
                response_type = response_model
            decorator_params.append(f"response_model={response_type}")
        decorator_params.append(f"status_code={status_code}")

        if handler_tags:
            decorator_params.append(f"tags={handler_tags}")

        decorator_line = f"@router.{method}(" + ", ".join(decorator_params) + ")"
        lines.append(decorator_line)

        func_signature_parts = []
        if async_handlers:
            func_signature_parts.append("async")
        func_signature_parts.append(f"def {handler_name}(")

        func_params = []
        for param_name, param_type in path_params:
            func_params.append(f"{param_name}: {param_type}")

        if request_model:
            func_params.append(f"payload: {request_model}")

        # Determine return type
        return_type = "None"
        if response_model:
            if many:
                return_type = f"List[{response_model}]"
            else:
                return_type = response_model

        func_signature = (
            " ".join(func_signature_parts) + ", ".join(func_params) + f") -> {return_type}:"
        )
        lines.append(func_signature)

        lines.append(f'    """Handler for {handler_name}."""')
        lines.append("    # TODO: implement")
        lines.append("    raise NotImplementedError")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    project_root = get_repo_root()
    spec_dir = project_root / "shared" / "spec"
    generated_dir = project_root / "shared" / "generated"

    models_file = spec_dir / "models.yaml"
    rest_file = spec_dir / "rest.yaml"

    if not models_file.exists():
        raise FileNotFoundError(f"Models spec not found: {models_file}")
    if not rest_file.exists():
        raise FileNotFoundError(f"REST spec not found: {rest_file}")

    models_spec = load_yaml(models_file)
    rest_spec = load_yaml(rest_file)

    schemas_content = generate_schemas(models_spec)
    router_content = generate_router(rest_spec, models_spec)

    schemas_file = generated_dir / "schemas.py"
    router_file = generated_dir / "routers" / "rest.py"

    generated_dir.mkdir(parents=True, exist_ok=True)
    router_file.parent.mkdir(parents=True, exist_ok=True)

    schemas_file.write_text(schemas_content)
    router_file.write_text(router_content)

    print(f"Generated {schemas_file}")
    print(f"Generated {router_file}")


if __name__ == "__main__":
    main()
