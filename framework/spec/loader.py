"""Unified spec loader with validation.

Loads all YAML specs and validates them using Pydantic models.
Provides clear error messages for spec violations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError
import yaml

from framework.spec.events import EventsSpec
from framework.spec.models import ModelsSpec
from framework.spec.routers import RouterSpec


class SpecValidationError(Exception):
    """Raised when spec validation fails."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        self.file_path = file_path
        self.message = message
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.file_path:
            return f"{self.file_path}: {self.message}"
        return self.message


@dataclass
class AllSpecs:
    """Container for all loaded and validated specs."""

    models: ModelsSpec
    routers: dict[str, RouterSpec]  # service_name/router_name -> RouterSpec
    events: EventsSpec


def load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    if not file_path.exists():
        raise SpecValidationError("File not found", str(file_path))

    try:
        with file_path.open() as f:
            data = yaml.safe_load(f)
            return data or {}
    except yaml.YAMLError as e:
        raise SpecValidationError(f"Invalid YAML syntax: {e}", str(file_path)) from e


def format_pydantic_error(error: ValidationError, context: str = "") -> str:
    """Format Pydantic validation error for human readability."""
    messages = []
    for err in error.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"]
        if context:
            messages.append(f"{context}.{loc}: {msg}")
        else:
            messages.append(f"{loc}: {msg}")
    return "\n".join(messages)


def load_models(models_file: Path) -> ModelsSpec:
    """Load and validate models.yaml."""
    data = load_yaml_file(models_file)

    try:
        return ModelsSpec.from_yaml(data)
    except ValidationError as e:
        raise SpecValidationError(format_pydantic_error(e, "models"), str(models_file)) from e
    except ValueError as e:
        raise SpecValidationError(str(e), str(models_file)) from e


def load_router(router_file: Path) -> RouterSpec:
    """Load and validate a single router spec."""
    data = load_yaml_file(router_file)

    try:
        return RouterSpec.from_yaml(data)
    except ValidationError as e:
        raise SpecValidationError(format_pydantic_error(e, "rest"), str(router_file)) from e
    except ValueError as e:
        raise SpecValidationError(str(e), str(router_file)) from e


def load_events(events_file: Path) -> EventsSpec:
    """Load and validate events.yaml."""
    if not events_file.exists():
        return EventsSpec(events=[])

    data = load_yaml_file(events_file)

    try:
        return EventsSpec.from_yaml(data)
    except ValidationError as e:
        raise SpecValidationError(format_pydantic_error(e, "events"), str(events_file)) from e
    except ValueError as e:
        raise SpecValidationError(str(e), str(events_file)) from e


def validate_model_references(
    models: ModelsSpec,
    routers: dict[str, RouterSpec],
    events: EventsSpec,
) -> list[str]:
    """Validate that all model references exist.

    Returns list of error messages.
    """
    errors = []
    known_models = models.get_model_names()

    # Check routers
    for router_name, router in routers.items():
        for handler in router.handlers:
            if handler.request_model and handler.request_model not in known_models:
                errors.append(
                    f"Router '{router_name}', handler '{handler.name}': "
                    f"Unknown request model '{handler.request_model}'"
                )
            if handler.response_model and handler.response_model not in known_models:
                errors.append(
                    f"Router '{router_name}', handler '{handler.name}': "
                    f"Unknown response model '{handler.response_model}'"
                )

    # Check events
    for event in events.events:
        if event.message and event.message not in known_models:
            errors.append(f"Event '{event.name}': Unknown message model '{event.message}'")

    return errors


def load_specs(repo_root: Path) -> AllSpecs:
    """Load and validate all specs from the repository.

    Args:
        repo_root: Path to the repository root

    Returns:
        AllSpecs containing validated models, routers, and events

    Raises:
        SpecValidationError: If any spec is invalid
    """
    # 1. Load models (required)
    shared_spec_dir = repo_root / "shared" / "spec"
    models_file = shared_spec_dir / "models.yaml"

    if not models_file.exists():
        raise SpecValidationError("models.yaml not found", str(models_file))

    models = load_models(models_file)

    # 2. Load events (optional)
    events_file = shared_spec_dir / "events.yaml"
    events = load_events(events_file)

    # 3. Load service routers
    routers: dict[str, RouterSpec] = {}
    services_dir = repo_root / "services"

    if services_dir.exists():
        for service_dir in services_dir.iterdir():
            if not service_dir.is_dir():
                continue

            spec_dir = service_dir / "spec"
            if not spec_dir.exists():
                continue

            for router_file in spec_dir.glob("*.yaml"):
                router_key = f"{service_dir.name}/{router_file.stem}"
                routers[router_key] = load_router(router_file)

    # 4. Cross-validate model references
    reference_errors = validate_model_references(models, routers, events)
    if reference_errors:
        raise SpecValidationError(
            "Model reference validation failed:\n" + "\n".join(f"  - {e}" for e in reference_errors)
        )

    return AllSpecs(models=models, routers=routers, events=events)


def validate_specs_cli(repo_root: Path) -> tuple[bool, str]:
    """CLI-friendly validation that returns success status and message.

    Returns:
        (success, message) tuple
    """
    try:
        specs = load_specs(repo_root)
        model_count = len(specs.models.models)
        router_count = len(specs.routers)
        event_count = len(specs.events.events)

        return True, (
            f"Spec validation PASSED.\n"
            f"  Models: {model_count}\n"
            f"  Routers: {router_count}\n"
            f"  Events: {event_count}"
        )
    except SpecValidationError as e:
        return False, f"Spec validation FAILED:\n  {e}"
