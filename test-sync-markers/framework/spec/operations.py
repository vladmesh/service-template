"""Operation specifications for unified transport abstraction.

This module defines the unified OperationSpec model that abstracts
over different transport types (REST, Events, gRPC in the future).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ParamSpec(BaseModel):
    """Specification for an operation parameter (path param, query param, etc)."""

    name: str
    type: str = "str"  # Python type annotation
    required: bool = True

    model_config = {"extra": "forbid"}


class RestConfig(BaseModel):
    """REST-specific configuration for an operation."""

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = ""
    status: int | None = None  # Default based on method if not specified

    model_config = {"extra": "forbid"}

    @property
    def effective_status(self) -> int:
        """Get the effective status code, using defaults if not specified."""
        if self.status is not None:
            return self.status
        if self.method == "POST":
            return 201
        if self.method == "DELETE":
            return 204
        return 200


class EventsConfig(BaseModel):
    """Events-specific configuration for an operation."""

    subscribe: str | None = None  # Channel to subscribe to
    publish_on_success: str | None = None  # Channel to publish after success

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_at_least_one(self) -> EventsConfig:
        """Ensure at least one direction is specified."""
        if not self.subscribe and not self.publish_on_success:
            msg = "Events config must have 'subscribe' or 'publish_on_success' (or both)"
            raise ValueError(msg)
        return self


class OperationSpec(BaseModel):
    """Unified specification for a single operation.

    An operation is transport-agnostic and can be exposed via REST, Events, or both.
    """

    name: str = ""  # Set by parent
    input_model: str | None = None
    output_model: str | None = None
    params: list[ParamSpec] = Field(default_factory=list)

    # Transport configurations (at least one required)
    rest: RestConfig | None = None
    events: EventsConfig | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_has_transport(self) -> OperationSpec:
        """Ensure at least one transport is configured."""
        if not self.rest and not self.events:
            msg = f"Operation '{self.name}' must have at least one transport (rest or events)"
            raise ValueError(msg)
        return self

    @property
    def response_many(self) -> bool:
        """Check if output is a list type."""
        if not self.output_model:
            return False
        return self.output_model.startswith("list[") or self.output_model.startswith("List[")

    @property
    def base_output_model(self) -> str | None:
        """Get the base output model (unwrapping list[] if present)."""
        if not self.output_model:
            return None
        if self.output_model.startswith("list[") and self.output_model.endswith("]"):
            return self.output_model[5:-1]
        if self.output_model.startswith("List[") and self.output_model.endswith("]"):
            return self.output_model[5:-1]
        return self.output_model

    @property
    def return_type(self) -> str:
        """Get the Python return type annotation."""
        return self.output_model or "None"

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> OperationSpec:
        """Create OperationSpec from raw YAML dict."""
        params = []
        for param_data in data.get("params", []):
            if isinstance(param_data, str):
                params.append(ParamSpec(name=param_data))
            else:
                params.append(ParamSpec.model_validate(param_data))

        rest_data = data.get("rest")
        rest = RestConfig.model_validate(rest_data) if rest_data else None

        events_data = data.get("events")
        events = EventsConfig.model_validate(events_data) if events_data else None

        return cls(
            name=name,
            input_model=data.get("input"),
            output_model=data.get("output"),
            params=params,
            rest=rest,
            events=events,
        )


class DomainConfig(BaseModel):
    """Domain-level configuration for REST and Events."""

    rest: RestDomainConfig | None = None

    model_config = {"extra": "forbid"}


class RestDomainConfig(BaseModel):
    """REST-specific domain configuration."""

    prefix: str = ""
    tags: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class DomainSpec(BaseModel):
    """Specification for a domain (group of related operations).

    A domain corresponds to a spec file like users.yaml.
    """

    name: str  # e.g., "users"
    config: DomainConfig = Field(default_factory=DomainConfig)
    operations: list[OperationSpec] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> DomainSpec:
        """Create DomainSpec from raw YAML dict."""
        # Parse config
        config_data = data.get("config", {})
        rest_config = config_data.get("rest")
        config = DomainConfig(
            rest=RestDomainConfig.model_validate(rest_config) if rest_config else None,
        )

        # Parse operations
        operations = []
        for op_name, op_data in data.get("operations", {}).items():
            operations.append(OperationSpec.from_yaml(op_name, op_data))

        return cls(name=name, config=config, operations=operations)

    def get_rest_operations(self) -> list[OperationSpec]:
        """Get operations that have REST transport configured."""
        return [op for op in self.operations if op.rest is not None]

    def get_events_operations(self) -> list[OperationSpec]:
        """Get operations that have Events transport configured."""
        return [op for op in self.operations if op.events is not None]


class ConsumeSpec(BaseModel):
    """Specification for consuming another service's operations.

    Used to declare dependencies on other services and generate typed clients.
    """

    service: str  # Provider service name, e.g., "backend"
    domain: str  # Domain to consume, e.g., "users"
    operations: list[str] = Field(default_factory=list)  # ["create_user"] or empty = all

    model_config = {"extra": "forbid"}

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> ConsumeSpec:
        """Create ConsumeSpec from raw YAML dict."""
        return cls.model_validate(data)


class ServiceManifest(BaseModel):
    """Per-service manifest defining dependencies and configuration.

    Loaded from services/<service>/spec/manifest.yaml.
    """

    service: str = ""  # Set by loader
    consumes: list[ConsumeSpec] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @classmethod
    def from_yaml(cls, service_name: str, data: dict[str, Any]) -> ServiceManifest:
        """Create ServiceManifest from raw YAML dict."""
        consumes = []
        for consume_data in data.get("consumes", []):
            consumes.append(ConsumeSpec.from_yaml(consume_data))

        return cls(service=service_name, consumes=consumes)
