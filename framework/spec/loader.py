"""Unified spec loader with validation.

Loads all YAML specs and validates them using Pydantic models.
Provides clear error messages for spec violations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError
import yaml

from framework.spec.events import EventsSpec
from framework.spec.models import ModelsSpec
from framework.spec.operations import DomainSpec, ServiceManifest


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
    events: EventsSpec
    domains: dict[str, DomainSpec] = field(default_factory=dict)
    manifests: dict[str, ServiceManifest] = field(default_factory=dict)


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


def load_domain(domain_file: Path) -> DomainSpec:
    """Load and validate a domain spec."""
    data = load_yaml_file(domain_file)

    domain_name = domain_file.stem
    try:
        return DomainSpec.from_yaml(domain_name, data)
    except ValidationError as e:
        raise SpecValidationError(format_pydantic_error(e, "domain"), str(domain_file)) from e
    except ValueError as e:
        raise SpecValidationError(str(e), str(domain_file)) from e


def load_manifest(manifest_file: Path, service_name: str) -> ServiceManifest:
    """Load and validate a service manifest."""
    data = load_yaml_file(manifest_file)

    try:
        return ServiceManifest.from_yaml(service_name, data)
    except ValidationError as e:
        raise SpecValidationError(format_pydantic_error(e, "manifest"), str(manifest_file)) from e
    except ValueError as e:
        raise SpecValidationError(str(e), str(manifest_file)) from e


def extract_base_model(model_ref: str) -> str:
    """Extract base model name from a model reference.

    Handles:
        - "User" -> "User"
        - "list[User]" -> "User"
        - "List[User]" -> "User"
    """
    if model_ref.startswith("list[") and model_ref.endswith("]"):
        return model_ref[5:-1]
    if model_ref.startswith("List[") and model_ref.endswith("]"):
        return model_ref[5:-1]
    return model_ref


def validate_model_references(
    models: ModelsSpec,
    domains: dict[str, DomainSpec],
    events: EventsSpec,
) -> list[str]:
    """Validate that all model references exist.

    Returns list of error messages.
    """
    errors = []
    known_models = models.get_model_names()

    # Check domains
    for domain_key, domain in domains.items():
        for op in domain.operations:
            if op.input_model:
                base_input = extract_base_model(op.input_model)
                if base_input not in known_models:
                    errors.append(
                        f"Domain '{domain_key}', operation '{op.name}': "
                        f"Unknown input model '{op.input_model}'"
                    )
            if op.output_model:
                base_output = extract_base_model(op.output_model)
                if base_output not in known_models:
                    errors.append(
                        f"Domain '{domain_key}', operation '{op.name}': "
                        f"Unknown output model '{op.output_model}'"
                    )

    # Check events
    for event in events.events:
        if event.message and event.message not in known_models:
            errors.append(f"Event '{event.name}': Unknown message model '{event.message}'")

    return errors


def validate_consume_references(
    manifests: dict[str, ServiceManifest],
    domains: dict[str, DomainSpec],
) -> list[str]:
    """Validate that all consumed service/domain/operation references exist.

    Returns list of error messages.
    """
    errors = []

    for service_name, manifest in manifests.items():
        for consume in manifest.consumes:
            domain_key = f"{consume.service}/{consume.domain}"

            # Check domain exists
            if domain_key not in domains:
                errors.append(
                    f"Manifest '{service_name}': consumes unknown domain "
                    f"'{consume.service}/{consume.domain}'"
                )
                continue

            domain = domains[domain_key]
            domain_op_names = {op.name for op in domain.operations}

            # Check operations if specific ones are listed
            if consume.operations:
                for op_name in consume.operations:
                    if op_name not in domain_op_names:
                        errors.append(
                            f"Manifest '{service_name}': consumes unknown operation "
                            f"'{op_name}' in domain '{domain_key}'"
                        )

    return errors


def _load_service_specs(
    services_dir: Path,
) -> tuple[dict[str, DomainSpec], dict[str, ServiceManifest]]:
    """Load domains and manifests from all services.

    Returns:
        Tuple of (domains, manifests) dicts
    """
    domains: dict[str, DomainSpec] = {}
    manifests: dict[str, ServiceManifest] = {}

    if not services_dir.exists():
        return domains, manifests

    for service_dir in services_dir.iterdir():
        if not service_dir.is_dir():
            continue

        spec_dir = service_dir / "spec"
        if not spec_dir.exists():
            continue

        service_name = service_dir.name

        # Load domain specs (*.yaml except manifest.yaml)
        for spec_file in spec_dir.glob("*.yaml"):
            if spec_file.stem == "manifest":
                continue
            domain_key = f"{service_name}/{spec_file.stem}"
            domains[domain_key] = load_domain(spec_file)

        # Load manifest if exists
        manifest_file = spec_dir / "manifest.yaml"
        if manifest_file.exists():
            manifests[service_name] = load_manifest(manifest_file, service_name)

    return domains, manifests


def load_specs(repo_root: Path) -> AllSpecs:
    """Load and validate all specs from the repository.

    Args:
        repo_root: Path to the repository root

    Returns:
        AllSpecs containing validated models, events, and domains

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

    # 3. Load service domains and manifests
    services_dir = repo_root / "services"
    domains, manifests = _load_service_specs(services_dir)

    # 4. Cross-validate model references
    reference_errors = validate_model_references(models, domains, events)
    if reference_errors:
        raise SpecValidationError(
            "Model reference validation failed:\n" + "\n".join(f"  - {e}" for e in reference_errors)
        )

    # 5. Validate manifest consumes references
    consume_errors = validate_consume_references(manifests, domains)
    if consume_errors:
        raise SpecValidationError(
            "Consume reference validation failed:\n" + "\n".join(f"  - {e}" for e in consume_errors)
        )

    return AllSpecs(models=models, events=events, domains=domains, manifests=manifests)


def validate_specs_cli(repo_root: Path) -> tuple[bool, str]:
    """CLI-friendly validation that returns success status and message.

    Returns:
        (success, message) tuple
    """
    try:
        specs = load_specs(repo_root)
        model_count = len(specs.models.models)
        domain_count = len(specs.domains)
        event_count = len(specs.events.events)
        manifest_count = len(specs.manifests)

        return True, (
            f"Spec validation PASSED.\n"
            f"  Models: {model_count}\n"
            f"  Domains: {domain_count}\n"
            f"  Events: {event_count}\n"
            f"  Manifests: {manifest_count}"
        )
    except SpecValidationError as e:
        return False, f"Spec validation FAILED:\n  {e}"
