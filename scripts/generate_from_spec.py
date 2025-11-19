"""Generate Pydantic schemas and FastAPI routers from YAML specifications."""

import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from jinja2 import Environment, FileSystemLoader
import yaml

from scripts.lib.env import get_repo_root


def load_yaml(file_path: Path) -> dict[str, Any]:
    """Load and parse YAML file."""
    with file_path.open() as f:
        return yaml.safe_load(f)


def map_type_to_json_schema(field_type: str) -> dict[str, Any]:
    """Map custom spec type to JSON Schema type."""
    mapping = {
        "int": {"type": "integer"},
        "string": {"type": "string"},
        "bool": {"type": "boolean"},
        "float": {"type": "number"},
        "datetime": {"type": "string", "format": "date-time"},
        "uuid": {"type": "string", "format": "uuid"},
    }
    return mapping.get(field_type, {"type": "string"})


def map_validations(field_def: dict[str, Any]) -> dict[str, Any]:
    """Map validation constraints to JSON Schema."""
    schema = {}
    if "ge" in field_def:
        schema["minimum"] = field_def["ge"]
    if "gt" in field_def:
        schema["exclusiveMinimum"] = field_def["gt"]
    if "le" in field_def:
        schema["maximum"] = field_def["le"]
    if "lt" in field_def:
        schema["exclusiveMaximum"] = field_def["lt"]
    if "min_length" in field_def:
        schema["minLength"] = field_def["min_length"]
    if "max_length" in field_def:
        schema["maxLength"] = field_def["max_length"]
    return schema


def convert_to_json_schema(models_spec: dict[str, Any]) -> dict[str, Any]:
    """Convert custom models.yaml format to JSON Schema definitions."""
    definitions = {}

    models = models_spec.get("models", {})

    for model_name, model_def in models.items():
        fields = model_def.get("fields", {})
        variants = model_def.get("variants", {})

        # Base model
        base_schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
            "title": model_name,
        }

        for field_name, field_def in fields.items():
            field_schema = map_type_to_json_schema(field_def.get("type", "string"))
            field_schema.update(map_validations(field_def))

            if "default" in field_def:
                field_schema["default"] = field_def["default"]

            base_schema["properties"][field_name] = field_schema

            # In the base model, we assume fields are required unless they have a default
            # or are explicitly optional (though the spec doesn't have an 'optional' flag
            # for base fields yet, usually it's handled in variants).
            if "default" not in field_def:
                base_schema["required"].append(field_name)

        definitions[model_name] = base_schema

        # Variants
        for variant_name, variant_def in variants.items():
            variant_full_name = f"{model_name}{variant_name}"
            exclude = set(variant_def.get("exclude", []))
            optional = set(variant_def.get("optional", []))

            variant_schema = {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
                "title": variant_full_name,
            }

            for field_name, field_def in fields.items():
                if field_name in exclude:
                    continue

                field_schema = map_type_to_json_schema(field_def.get("type", "string"))
                field_schema.update(map_validations(field_def))

                # If it's optional in variant, we don't add to required
                # We also strip 'default' if we want to force it to be passed?
                # Usually 'optional' means it can be omitted.

                if "default" in field_def:
                    field_schema["default"] = field_def["default"]

                variant_schema["properties"][field_name] = field_schema

                is_optional = field_name in optional
                has_default = "default" in field_def

                if not is_optional and not has_default:
                    variant_schema["required"].append(field_name)

            definitions[variant_full_name] = variant_schema

    return {"definitions": definitions}


def generate_schemas(models_file: Path, output_file: Path) -> None:
    """Generate Pydantic models using datamodel-code-generator."""
    models_spec = load_yaml(models_file)
    json_schema = convert_to_json_schema(models_spec)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as tmp:
        json.dump(json_schema, tmp, indent=2)
        tmp.flush()

        cmd = [
            "datamodel-codegen",
            "--input",
            tmp.name,
            "--input-file-type",
            "jsonschema",
            "--output",
            str(output_file),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-schema-description",
            "--use-field-description",
            "--disable-timestamp",  # We want datetime, but maybe not custom Timestamp types
            "--use-standard-collections",
            "--use-union-operator",
        ]

        subprocess.run(cmd, check=True)  # noqa: S603


def get_python_type_for_param(param_type: str) -> str:
    """Map spec type to Python type for function signatures."""
    mapping = {
        "int": "int",
        "string": "str",
        "bool": "bool",
        "uuid": "UUID",
        "float": "float",
        "datetime": "datetime",
    }
    return mapping.get(param_type, "str")


def prepare_router_context(
    rest_spec: dict[str, Any], models_spec: dict[str, Any]
) -> dict[str, Any]:
    """Prepare context for Jinja2 template."""
    rest = rest_spec.get("rest", {})
    router_config = rest.get("router", {})
    handlers_spec = rest.get("handlers", {})

    context = {
        "prefix": router_config.get("prefix", ""),
        "tags": router_config.get("tags", []),
        "async_handlers": router_config.get("async_handlers", True),
        "imports": set(),
        "handlers": [],
    }

    for name, def_ in handlers_spec.items():
        handler = {
            "name": name,
            "method": def_.get("method", "GET"),
            "path": def_.get("path", "/"),
            "status_code": def_.get("response", {}).get("status_code"),
            "tags": def_.get("tags"),
            "docstring": f"Handler for {name}",
            "params": [],
            "request_model": None,
            "response_model": None,
            "return_type": "None",
        }

        # Status code default
        if handler["status_code"] is None:
            handler["status_code"] = 201 if handler["method"].upper() == "POST" else 200

        # Path params
        # Simple extraction: {param}
        import re

        path_params = re.findall(r"\{(\w+)\}", handler["path"])
        for param in path_params:
            # We assume path params are int by default if not specified (legacy behavior?)
            # Or we should look at some definition. The original script assumed 'int'.
            # Let's stick to 'int' for now as per original script, or maybe 'str' is safer?
            # Original: return [(match, "int") for match in matches]
            handler["params"].append({"name": param, "type": "int"})

        # Request model
        req_def = def_.get("request")
        if req_def:
            model = req_def.get("model")
            variant = req_def.get("variant")
            full_name = f"{model}{variant}" if variant else model
            handler["request_model"] = full_name
            context["imports"].add(full_name)

        # Response model
        res_def = def_.get("response")
        if res_def:
            model = res_def.get("model")
            if model:
                variant = res_def.get("variant")
                full_name = f"{model}{variant}" if variant else model
                many = res_def.get("many", False)

                handler["response_model"] = f"List[{full_name}]" if many else full_name
                handler["return_type"] = handler["response_model"]
                context["imports"].add(full_name)

        context["handlers"].append(handler)

    return context


def generate_router(rest_file: Path, models_file: Path, output_file: Path) -> None:
    """Generate FastAPI router using Jinja2."""
    rest_spec = load_yaml(rest_file)
    models_spec = load_yaml(models_file)

    context = prepare_router_context(rest_spec, models_spec)

    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # Generating Python code, not HTML  # noqa: S701
    )
    template = env.get_template("router.py.j2")

    content = template.render(**context)
    output_file.write_text(content)


def main() -> None:
    """Main entry point."""
    project_root = get_repo_root()
    spec_dir = project_root / "shared" / "spec"
    routers_spec_dir = spec_dir / "routers"
    generated_dir = project_root / "shared" / "generated"

    models_file = spec_dir / "models.yaml"

    if not models_file.exists():
        print("Models spec not found.")
        return

    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / "routers").mkdir(parents=True, exist_ok=True)

    print("Generating schemas...")
    generate_schemas(models_file, generated_dir / "schemas.py")

    if routers_spec_dir.exists():
        for router_file in routers_spec_dir.glob("*.yaml"):
            print(f"Generating router for {router_file.stem}...")
            output_file = generated_dir / "routers" / f"{router_file.stem}.py"
            generate_router(router_file, models_file, output_file)
    else:
        print("No routers directory found, skipping router generation.")

    # Clean up old rest.py if it exists (optional, but good for hygiene)
    old_rest = generated_dir / "routers" / "rest.py"
    if old_rest.exists():
        print("Removing obsolete routers/rest.py")
        old_rest.unlink()

    print("Done.")


if __name__ == "__main__":
    main()
