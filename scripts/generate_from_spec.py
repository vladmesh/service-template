"""Generate Pydantic schemas and FastAPI routers from YAML specifications."""

import json
from pathlib import Path
import subprocess
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
    if field_type.startswith("list[") and field_type.endswith("]"):
        inner_type = field_type[5:-1]
        return {
            "type": "array",
            "items": map_type_to_json_schema(inner_type),
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


def process_field_schema(field_name: str, field_def: dict[str, Any]) -> dict[str, Any]:
    """Process a single field definition into JSON Schema."""
    field_schema = map_type_to_json_schema(field_def.get("type", "string"))
    field_schema.update(map_validations(field_def))

    if "default" in field_def:
        field_schema["default"] = field_def["default"]

    if field_def.get("readonly", False):
        field_schema["readOnly"] = True

    return field_schema


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
            field_schema = process_field_schema(field_name, field_def)
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

                # Auto-exclude readonly fields from Create/Update variants
                if field_def.get("readonly", False) and variant_name in ("Create", "Update"):
                    continue

                field_schema = process_field_schema(field_name, field_def)
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

    # Use fixed filename to ensure stable filename comment in generated code
    tmp_path = output_file.parent / "models_schema.json"

    try:
        with tmp_path.open("w") as tmp:
            json.dump(json_schema, tmp, indent=2)

        cmd = [
            "datamodel-codegen",
            "--input",
            str(tmp_path),
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
    finally:
        # Clean up temporary file
        tmp_path.unlink(missing_ok=True)


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
    rest_spec: dict[str, Any], models_spec: dict[str, Any], module_name: str
) -> dict[str, Any]:
    """Prepare context for Jinja2 template."""
    rest = rest_spec.get("rest", {})
    router_config = rest.get("router", {})
    handlers_spec = rest.get("handlers", {})

    context = {
        "module_name": module_name,
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
            # Infer type based on name (heuristic)
            # Default to int for IDs as per project convention
            param_type = "int" if param.endswith("_id") else "str"
            handler["params"].append({"name": param, "type": param_type, "source": "Path(...)"})
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


def generate_protocols(routers_dir: Path, models_file: Path, output_file: Path) -> None:
    """Generate protocols for all routers."""
    models_spec = load_yaml(models_file)

    routers_context = []
    all_imports = set()

    for router_file in sorted(routers_dir.glob("*.yaml")):
        rest_spec = load_yaml(router_file)
        module_name = router_file.stem
        # Capitalize first letter for Protocol name (e.g. users -> UsersControllerProtocol)
        protocol_name = f"{module_name.capitalize()}ControllerProtocol"

        context = prepare_router_context(rest_spec, models_spec, module_name)
        context["name"] = module_name
        context["protocol_name"] = protocol_name

        routers_context.append(context)
        all_imports.update(context["imports"])

    # Use separate environment without lstrip_blocks to preserve indentation
    # for protocol methods inside class
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=False,  # Keep indentation for protocol methods inside class
        autoescape=False,  # Generating Python code, not HTML  # noqa: S701
    )
    template = env.get_template("protocols.py.j2")

    content = template.render(routers=routers_context, imports=all_imports, async_handlers=True)
    output_file.write_text(content)
    print(f"Generated protocols: {output_file}")


def generate_router(rest_file: Path, models_file: Path, output_file: Path) -> None:
    """Generate FastAPI router using Jinja2."""
    rest_spec = load_yaml(rest_file)
    models_spec = load_yaml(models_file)
    module_name = rest_file.stem

    context = prepare_router_context(rest_spec, models_spec, module_name)
    context["protocol_name"] = f"{module_name.capitalize()}ControllerProtocol"

    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # Generating Python code, not HTML  # noqa: S701
    )
    template = env.get_template("router.py.j2")

    content = template.render(**context)
    output_file.write_text(content)


def generate_controller(rest_file: Path, models_file: Path, output_file: Path) -> None:
    """Generate FastAPI controller stub using Jinja2 (only if not exists)."""
    if output_file.exists():
        print(f"Controller {output_file.name} already exists, skipping.")
        return

    rest_spec = load_yaml(rest_file)
    models_spec = load_yaml(models_file)
    module_name = rest_file.stem

    context = prepare_router_context(rest_spec, models_spec, module_name)
    context["protocol_name"] = f"{module_name.capitalize()}ControllerProtocol"

    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # Generating Python code, not HTML  # noqa: S701
    )
    template = env.get_template("controller.py.j2")

    content = template.render(**context)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content)
    print(f"Generated controller: {output_file}")


def main() -> None:
    """Main entry point."""
    project_root = get_repo_root()
    spec_dir = project_root / "shared" / "spec"
    routers_spec_dir = spec_dir / "routers"
    generated_dir = project_root / "shared" / "shared" / "generated"

    # Controllers location
    controllers_dir = project_root / "services" / "backend" / "src" / "controllers"

    models_file = spec_dir / "models.yaml"

    if not models_file.exists():
        print("Models spec not found.")
        return

    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / "routers").mkdir(parents=True, exist_ok=True)
    controllers_dir.mkdir(parents=True, exist_ok=True)

    print("Generating schemas...")
    generate_schemas(models_file, generated_dir / "schemas.py")

    if routers_spec_dir.exists():
        print("Generating protocols...")
        generate_protocols(routers_spec_dir, models_file, generated_dir / "protocols.py")

        for router_file in routers_spec_dir.glob("*.yaml"):
            print(f"Processing {router_file.stem}...")

            # Generate Router
            router_output = generated_dir / "routers" / f"{router_file.stem}.py"
            generate_router(router_file, models_file, router_output)

            # Generate Controller
            controller_output = controllers_dir / f"{router_file.stem}.py"
            generate_controller(router_file, models_file, controller_output)
    else:
        print("No routers directory found, skipping router generation.")

    events_file = spec_dir / "events.yaml"
    generate_events(events_file, generated_dir / "events.py")

    print("Done.")


def generate_events(events_file: Path, output_file: Path) -> None:
    """Generate FastStream events module."""
    if not events_file.exists():
        print("No events.yaml found, skipping event generation.")
        return

    events_spec = load_yaml(events_file)
    events = []
    imports = set()

    for name, def_ in events_spec.get("events", {}).items():
        msg_type = def_.get("message")
        events.append(
            {
                "name": name,
                "message": msg_type,
                "publish": def_.get("publish", False),
                "subscribe": def_.get("subscribe", False),
            }
        )
        if msg_type:
            imports.add(msg_type)

    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # noqa: S701
    )
    template = env.get_template("events.py.j2")

    content = template.render(events=events, imports=imports)
    output_file.write_text(content)
    print(f"Generated events: {output_file}")


if __name__ == "__main__":
    main()
