"""Validate YAML specifications before code generation.

This module provides early validation of spec files to catch errors
before they propagate to generated code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import sys
from typing import Any

import yaml

from framework.lib.env import get_repo_root

# Valid primitive types supported by the generator
VALID_TYPES = frozenset({"int", "string", "bool", "float", "datetime", "uuid"})

# Valid HTTP methods
VALID_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})

# Valid validation constraints
VALID_CONSTRAINTS = frozenset(
    {
        "ge",
        "gt",
        "le",
        "lt",  # numeric
        "min_length",
        "max_length",  # string
        "default",
        "readonly",
        "type",
    }
)


@dataclass
class ValidationError:
    """Represents a single validation error."""

    file: str
    message: str
    path: str = ""  # YAML path like "models.User.fields.id"

    def __str__(self) -> str:
        location = f"{self.file}"
        if self.path:
            location += f" ({self.path})"
        return f"{location}: {self.message}"


@dataclass
class ValidationResult:
    """Aggregates validation errors."""

    errors: list[ValidationError] = field(default_factory=list)

    def add(self, file: str, message: str, path: str = "") -> None:
        self.errors.append(ValidationError(file=file, message=message, path=path))

    def has_errors(self) -> bool:
        return bool(self.errors)

    def merge(self, other: ValidationResult) -> None:
        self.errors.extend(other.errors)


def load_yaml(file_path: Path) -> dict[str, Any] | None:
    """Load YAML file, return None if not found or invalid."""
    if not file_path.exists():
        return None
    try:
        with file_path.open() as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return None


def is_valid_type(type_str: str) -> bool:
    """Check if type string is valid (including list[T])."""
    if type_str in VALID_TYPES:
        return True
    # Check for list[T] pattern
    if type_str.startswith("list[") and type_str.endswith("]"):
        inner = type_str[5:-1]
        return is_valid_type(inner)
    return False


def _validate_model_fields(
    fields: dict[str, Any],
    model_name: str,
    file_name: str,
    result: ValidationResult,
) -> None:
    """Validate fields of a single model."""
    for field_name, field_def in fields.items():
        path = f"models.{model_name}.fields.{field_name}"
        if not isinstance(field_def, dict):
            result.add(file_name, "Field definition must be a dict", path)
            continue

        # Check type
        field_type = field_def.get("type")
        if not field_type:
            result.add(file_name, "Field missing 'type'", path)
        elif not is_valid_type(field_type):
            result.add(file_name, f"Unknown type '{field_type}'", path)

        # Check for unknown keys
        for key in field_def:
            if key not in VALID_CONSTRAINTS:
                result.add(file_name, f"Unknown field constraint '{key}'", path)


def _validate_model_variants(
    variants: dict[str, Any],
    field_names: set[str],
    model_name: str,
    file_name: str,
    result: ValidationResult,
) -> None:
    """Validate variants of a single model."""
    for variant_name, variant_def in variants.items():
        path = f"models.{model_name}.variants.{variant_name}"
        if variant_def is None:
            continue
        if not isinstance(variant_def, dict):
            result.add(file_name, "Variant definition must be a dict or empty", path)
            continue

        # Check exclude references
        for excluded_field in variant_def.get("exclude", []):
            if excluded_field not in field_names:
                result.add(file_name, f"Excluded field '{excluded_field}' does not exist", path)

        # Check optional references
        for optional_field in variant_def.get("optional", []):
            if optional_field not in field_names:
                result.add(file_name, f"Optional field '{optional_field}' does not exist", path)


def validate_models(spec: dict[str, Any], file_name: str) -> ValidationResult:
    """Validate models.yaml specification."""
    result = ValidationResult()
    models = spec.get("models", {})

    if not models:
        result.add(file_name, "No models defined", "models")
        return result

    for model_name, model_def in models.items():
        if not isinstance(model_def, dict):
            result.add(file_name, "Model definition must be a dict", f"models.{model_name}")
            continue

        fields = model_def.get("fields", {})
        if not fields:
            result.add(file_name, "Model has no fields", f"models.{model_name}")
            continue

        _validate_model_fields(fields, model_name, file_name, result)
        _validate_model_variants(
            model_def.get("variants", {}),
            set(fields.keys()),
            model_name,
            file_name,
            result,
        )

    return result


def get_all_model_variants(models_spec: dict[str, Any]) -> dict[str, set[str]]:
    """Extract model names and their variants from models.yaml."""
    result: dict[str, set[str]] = {}
    models = models_spec.get("models", {})

    for model_name, model_def in models.items():
        if not isinstance(model_def, dict):
            continue
        variants = set(model_def.get("variants", {}).keys())
        # Base model is always available (no variant suffix)
        variants.add("")
        result[model_name] = variants

    return result


def validate_router(
    spec: dict[str, Any],
    file_name: str,
    model_variants: dict[str, set[str]],
) -> ValidationResult:
    """Validate a router YAML specification."""
    result = ValidationResult()
    rest = spec.get("rest", {})

    if not rest:
        result.add(file_name, "Missing 'rest' section")
        return result

    handlers = rest.get("handlers", {})
    if not handlers:
        result.add(file_name, "No handlers defined", "rest.handlers")
        return result

    for handler_name, handler_def in handlers.items():
        if not isinstance(handler_def, dict):
            result.add(
                file_name,
                "Handler definition must be a dict",
                f"rest.handlers.{handler_name}",
            )
            continue

        # Validate HTTP method
        method = handler_def.get("method", "GET").upper()
        if method not in VALID_METHODS:
            result.add(
                file_name,
                f"Invalid HTTP method '{method}'",
                f"rest.handlers.{handler_name}",
            )

        # Validate path
        path = handler_def.get("path", "/")
        path_params = re.findall(r"\{(\w+)\}", path)

        # Check for duplicate path params
        if len(path_params) != len(set(path_params)):
            result.add(
                file_name,
                "Duplicate path parameters",
                f"rest.handlers.{handler_name}.path",
            )

        # Validate request model
        request = handler_def.get("request")
        if request:
            _validate_model_ref(
                request,
                model_variants,
                file_name,
                f"rest.handlers.{handler_name}.request",
                result,
            )

        # Validate response model
        response = handler_def.get("response")
        if response:
            model = response.get("model")
            if model is not None:  # model: null is valid (e.g., 204 responses)
                _validate_model_ref(
                    response,
                    model_variants,
                    file_name,
                    f"rest.handlers.{handler_name}.response",
                    result,
                )

    return result


def _validate_model_ref(
    ref: dict[str, Any],
    model_variants: dict[str, set[str]],
    file_name: str,
    path: str,
    result: ValidationResult,
) -> None:
    """Validate a model reference (request or response)."""
    model = ref.get("model")
    variant = ref.get("variant", "")

    if not model:
        result.add(file_name, "Missing 'model' in reference", path)
        return

    if model not in model_variants:
        result.add(file_name, f"Unknown model '{model}'", path)
        return

    if variant and variant not in model_variants[model]:
        available = ", ".join(sorted(v for v in model_variants[model] if v))
        result.add(
            file_name,
            f"Unknown variant '{variant}' for model '{model}'. Available: {available}",
            path,
        )


def validate_events(
    spec: dict[str, Any],
    file_name: str,
    model_variants: dict[str, set[str]],
) -> ValidationResult:
    """Validate events.yaml specification."""
    result = ValidationResult()
    events = spec.get("events", {})

    if not events:
        # events.yaml can be empty or missing
        return result

    for event_name, event_def in events.items():
        if not isinstance(event_def, dict):
            result.add(
                file_name,
                "Event definition must be a dict",
                f"events.{event_name}",
            )
            continue

        message = event_def.get("message")
        if not message:
            result.add(
                file_name,
                "Event missing 'message' type",
                f"events.{event_name}",
            )
            continue

        if message not in model_variants:
            result.add(
                file_name,
                f"Unknown message type '{message}'",
                f"events.{event_name}",
            )

    return result


def validate_all_specs(repo_root: Path) -> ValidationResult:
    """Validate all spec files in the repository."""
    result = ValidationResult()

    # 1. Validate shared models.yaml
    shared_spec_dir = repo_root / "shared" / "spec"
    models_file = shared_spec_dir / "models.yaml"

    models_spec = load_yaml(models_file)
    if models_spec is None:
        result.add(str(models_file.relative_to(repo_root)), "File not found or invalid YAML")
        return result

    models_result = validate_models(models_spec, str(models_file.relative_to(repo_root)))
    result.merge(models_result)

    # Get model variants for cross-validation
    model_variants = get_all_model_variants(models_spec)

    # 2. Validate shared events.yaml
    events_file = shared_spec_dir / "events.yaml"
    events_spec = load_yaml(events_file)
    if events_spec:
        events_result = validate_events(
            events_spec,
            str(events_file.relative_to(repo_root)),
            model_variants,
        )
        result.merge(events_result)

    # 3. Validate service-level router specs
    services_dir = repo_root / "services"
    if services_dir.exists():
        for service_dir in services_dir.iterdir():
            if not service_dir.is_dir():
                continue

            spec_dir = service_dir / "spec"
            if not spec_dir.exists():
                continue

            for router_file in spec_dir.glob("*.yaml"):
                router_spec = load_yaml(router_file)
                if router_spec is None:
                    result.add(
                        str(router_file.relative_to(repo_root)),
                        "Invalid YAML syntax",
                    )
                    continue

                router_result = validate_router(
                    router_spec,
                    str(router_file.relative_to(repo_root)),
                    model_variants,
                )
                result.merge(router_result)

    return result


def main() -> int:
    """Main entry point."""
    repo_root = get_repo_root()
    result = validate_all_specs(repo_root)

    if result.has_errors():
        print("Spec validation FAILED:\n")
        for error in result.errors:
            print(f"  - {error}")
        return 1

    print("Spec validation PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
