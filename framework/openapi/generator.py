"""OpenAPI 3.1 specification generator from internal specs.

Generates a complete OpenAPI specification from:
- models.yaml → JSON Schema definitions in components/schemas
- routers/*.yaml → paths and operations
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from framework.lib.env import get_repo_root
from framework.spec.loader import AllSpecs, load_specs
from framework.spec.routers import HandlerSpec


def type_to_openapi_schema(type_str: str) -> dict[str, Any]:
    """Convert type string to OpenAPI schema reference."""
    # If it's a model reference, use $ref
    if type_str and type_str[0].isupper():
        return {"$ref": f"#/components/schemas/{type_str}"}

    # Primitive type mapping
    mapping = {
        "int": {"type": "integer"},
        "string": {"type": "string"},
        "str": {"type": "string"},
        "bool": {"type": "boolean"},
        "float": {"type": "number"},
        "UUID": {"type": "string", "format": "uuid"},
    }
    return mapping.get(type_str, {"type": "string"})


class OpenAPIGenerator:
    """Generate OpenAPI 3.1 specification from validated specs."""

    def __init__(self, specs: AllSpecs) -> None:
        """Initialize with validated specs."""
        self.specs = specs

    def generate(
        self,
        title: str = "API",
        version: str = "1.0.0",
        description: str = "",
        service_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate complete OpenAPI 3.1 specification."""
        openapi = {
            "openapi": "3.1.0",
            "info": {
                "title": title,
                "version": version,
                "description": description,
            },
            "paths": self._generate_paths(service_name),
            "components": {
                "schemas": self._generate_schemas(),
            },
        }
        return openapi

    def _generate_schemas(self) -> dict[str, Any]:
        """Generate JSON Schema definitions from models."""
        schemas = {}

        for model_name, model_spec in self.specs.models.models.items():
            # Base model
            schemas[model_name] = self._model_to_schema(model_spec, model_name)

            # Variants
            for variant_name in model_spec.variants:
                variant_full_name = f"{model_name}{variant_name}"
                fields = model_spec.get_variant_fields(variant_name)
                schemas[variant_full_name] = self._variant_to_schema(
                    model_name, variant_name, fields
                )

        return schemas

    def _model_to_schema(self, model_spec, model_name: str) -> dict[str, Any]:
        """Convert ModelSpec to JSON Schema."""
        properties = {}
        required = []

        for field_name, field_spec in model_spec.fields.items():
            properties[field_name] = field_spec.to_json_schema()
            if field_spec.default is None and not field_name.startswith("_"):
                required.append(field_name)

        return {
            "type": "object",
            "title": model_name,
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    def _variant_to_schema(
        self, model_name: str, variant_name: str, fields: dict
    ) -> dict[str, Any]:
        """Convert variant fields to JSON Schema."""
        properties = {}
        required = []

        for field_name, field_spec in fields.items():
            properties[field_name] = field_spec.to_json_schema()
            if field_spec.default is None:
                required.append(field_name)

        return {
            "type": "object",
            "title": f"{model_name}{variant_name}",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    def _generate_paths(self, service_name: str | None = None) -> dict[str, Any]:
        """Generate OpenAPI paths from routers."""
        paths: dict[str, Any] = {}

        for router_key, router in self.specs.routers.items():
            # router_key is "service/router"
            r_service, _ = router_key.split("/")

            if service_name and r_service != service_name:
                continue

            for handler in router.handlers:
                path = f"{router.prefix}{handler.path}"
                if path.endswith("/") and len(path) > 1:
                    path = path[:-1]
                # Convert {param} to OpenAPI format (it's already correct)
                if not path:
                    path = "/"

                if path not in paths:
                    paths[path] = {}

                operation = self._handler_to_operation(handler, router.tags)
                paths[path][handler.method.lower()] = operation

        return paths

    def _handler_to_operation(self, handler: HandlerSpec, tags: list[str]) -> dict[str, Any]:
        """Convert handler to OpenAPI operation."""
        operation: dict[str, Any] = {
            "operationId": handler.name,
            "summary": handler.name.replace("_", " ").title(),
            "tags": tags,
            "responses": {},
        }

        # Path parameters
        path_params = handler.get_path_params()
        if path_params:
            operation["parameters"] = [
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": type_to_openapi_schema(param_type),
                }
                for name, param_type in path_params
            ]

        # Request body
        if handler.request_model:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{handler.request_model}"},
                    },
                },
            }

        # Response
        status = str(handler.status_code)
        if handler.response_model:
            response_schema: dict[str, Any]
            if handler.response_many:
                response_schema = {
                    "type": "array",
                    "items": {"$ref": f"#/components/schemas/{handler.response_model}"},
                }
            else:
                response_schema = {"$ref": f"#/components/schemas/{handler.response_model}"}

            operation["responses"][status] = {
                "description": "Successful response",
                "content": {
                    "application/json": {"schema": response_schema},
                },
            }
        else:
            operation["responses"][status] = {
                "description": "No content",
            }

        return operation


def generate_openapi(
    repo_root: Path | None = None,
    output_path: Path | None = None,
    title: str = "API",
    version: str = "1.0.0",
    service_name: str | None = None,
) -> dict[str, Any]:
    """Generate OpenAPI spec and optionally write to file.

    Args:
        repo_root: Repository root path
        output_path: If provided, write JSON to this path
        title: API title
        version: API version
        service_name: Optional service name to filter routers

    Returns:
        The generated OpenAPI specification dict
    """
    if repo_root is None:
        repo_root = get_repo_root()

    specs = load_specs(repo_root)
    generator = OpenAPIGenerator(specs)
    openapi = generator.generate(title=title, version=version, service_name=service_name)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(openapi, f, indent=2)

    return openapi


def main() -> None:
    """CLI entrypoint for OpenAPI generation."""
    repo_root = get_repo_root()
    services_dir = repo_root / "services"

    if not services_dir.exists():
        print("No services directory found.")
        return

    generated_count = 0

    for service_dir in services_dir.iterdir():
        if not service_dir.is_dir():
            continue

        service_name = service_dir.name

        # Check if service has any routers defined
        spec_dir = service_dir / "spec"
        has_routers = spec_dir.exists() and any(spec_dir.glob("*.yaml"))

        if not has_routers:
            continue

        output_path = service_dir / "docs" / "openapi.json"
        generate_openapi(
            repo_root=repo_root,
            output_path=output_path,
            title=f"{service_name.title()} API",
            service_name=service_name,
        )
        print(f"Generated OpenAPI spec for {service_name}: {output_path.relative_to(repo_root)}")
        generated_count += 1

    if generated_count == 0:
        print("No services with router specs found.")


if __name__ == "__main__":
    main()
