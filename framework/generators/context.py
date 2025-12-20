"""Operation context builder for code generation.

Provides a unified way to build template context for operations,
eliminating duplication between routers, protocols, and controllers generators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from framework.spec.operations import OperationSpec


@dataclass
class ParamContext:
    """Context for a single parameter in generated code."""

    name: str
    type: str
    required: bool = True
    source: str | None = None  # e.g., "Path(...)" for REST


@dataclass
class OperationContext:
    """Complete context for generating code for an operation.

    This is the unified structure used by all generators (routers, protocols,
    controllers, event handlers).
    """

    name: str
    params: list[ParamContext] = field(default_factory=list)
    input_model: str | None = None
    output_model: str | None = None
    return_type: str = "None"
    imports: set[str] = field(default_factory=set)

    # REST-specific (populated only for REST operations)
    http_method: str | None = None
    path: str | None = None
    status_code: int | None = None
    response_many: bool = False  # True if response is list[Model]

    # Events-specific (populated only for Events operations)
    subscribe_channel: str | None = None
    publish_channel: str | None = None

    @property
    def computed_return_type(self) -> str:
        """Get return type, handling response_many."""
        if not self.output_model:
            return "None"
        if self.response_many:
            return f"list[{self.output_model}]"
        return self.output_model


class OperationContextBuilder:
    """Builds OperationContext from OperationSpec.

    Eliminates code duplication by centralizing all the logic for:
    - Extracting path parameters
    - Building import lists
    - Determining return types
    - Adding transport-specific data
    """

    def build(
        self,
        operation: OperationSpec,
        *,
        include_rest: bool = True,
        include_events: bool = True,
    ) -> OperationContext:
        """Build a complete OperationContext from an OperationSpec.

        Args:
            operation: The operation specification
            include_rest: Whether to include REST-specific context
            include_events: Whether to include Events-specific context

        Returns:
            OperationContext ready for template rendering
        """
        imports: set[str] = set()
        params: list[ParamContext] = []

        # Collect models for imports (use base models, not wrapped types)
        if operation.input_model:
            imports.add(operation.input_model)
        if operation.base_output_model:
            imports.add(operation.base_output_model)

        # Build params from spec
        for param in operation.params:
            params.append(
                ParamContext(
                    name=param.name,
                    type=param.type,
                    required=param.required,
                )
            )

        # Build base context
        ctx = OperationContext(
            name=operation.name,
            params=params,
            input_model=operation.input_model,
            output_model=operation.base_output_model,  # Use unwrapped model
            return_type=operation.return_type,
            imports=imports,
            response_many=operation.response_many,  # Pass the list flag
        )

        # Add REST-specific context
        if include_rest and operation.rest:
            ctx.http_method = operation.rest.method
            ctx.path = operation.rest.path
            ctx.status_code = operation.rest.effective_status

            # Add Path(...) source for REST params
            for param in ctx.params:
                param.source = "Path(...)"

        # Add Events-specific context
        if include_events and operation.events:
            ctx.subscribe_channel = operation.events.subscribe
            ctx.publish_channel = operation.events.publish_on_success

        return ctx

    def build_for_protocol(self, operation: OperationSpec) -> OperationContext:
        """Build context specifically for Protocol generation.

        Protocols are transport-agnostic, so we exclude transport-specific data.
        """
        return self.build(operation, include_rest=False, include_events=False)

    def build_for_rest(self, operation: OperationSpec) -> OperationContext:
        """Build context specifically for REST router generation."""
        if not operation.rest:
            msg = f"Operation '{operation.name}' has no REST transport configured"
            raise ValueError(msg)
        return self.build(operation, include_rest=True, include_events=False)

    def build_for_events(self, operation: OperationSpec) -> OperationContext:
        """Build context specifically for Events handler generation."""
        if not operation.events:
            msg = f"Operation '{operation.name}' has no Events transport configured"
            raise ValueError(msg)
        return self.build(operation, include_rest=False, include_events=True)
