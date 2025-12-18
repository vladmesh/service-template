"""Router specifications for REST API validation.

Defines the structure of routers/*.yaml:
- RouterSpec: Configuration for a router (prefix, tags)
- HandlerSpec: A single HTTP endpoint handler
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Valid HTTP methods
HTTP_METHODS = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class ResponseSpec(BaseModel):
    """Specification for handler response."""

    model: str | None = None
    variant: str | None = None  # Legacy format: model + variant
    many: bool = False
    status_code: int | None = None

    model_config = {"extra": "forbid"}

    @property
    def full_model_name(self) -> str | None:
        """Get full model name combining model+variant if present."""
        if self.model is None:
            return None
        if self.variant:
            return f"{self.model}{self.variant}"
        return self.model


class RequestSpec(BaseModel):
    """Specification for handler request (legacy format support)."""

    model: str
    variant: str | None = None

    model_config = {"extra": "forbid"}

    @property
    def full_model_name(self) -> str:
        """Get full model name combining model+variant if present."""
        if self.variant:
            return f"{self.model}{self.variant}"
        return self.model


class HandlerSpec(BaseModel):
    """Specification for a single HTTP handler."""

    name: str = ""  # Set by parent
    method: HTTP_METHODS
    path: str = "/"
    request: str | RequestSpec | None = None  # Request model name or spec
    response: str | ResponseSpec | None = None
    status: int | None = None  # Can also be in response
    params: dict[str, str] = Field(default_factory=dict)  # Override path param types

    model_config = {"extra": "forbid"}

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        """Normalize HTTP method to uppercase."""
        return v.upper()

    @property
    def status_code(self) -> int:
        """Get the effective status code."""
        # Explicit status takes priority
        if self.status is not None:
            return self.status

        # Then response.status_code
        if isinstance(self.response, ResponseSpec) and self.response.status_code is not None:
            return self.response.status_code

        # Defaults based on method
        if self.method == "POST":
            return 201
        if self.method == "DELETE":
            return 204
        return 200

    @property
    def request_model(self) -> str | None:
        """Get the request model name."""
        if self.request is None:
            return None
        if isinstance(self.request, str):
            return self.request
        return self.request.full_model_name

    @property
    def response_model(self) -> str | None:
        """Get the response model name."""
        if self.response is None:
            return None
        if isinstance(self.response, str):
            return self.response
        return self.response.full_model_name

    @property
    def response_many(self) -> bool:
        """Check if response is a list."""
        if isinstance(self.response, ResponseSpec):
            return self.response.many
        return False

    def get_path_params(self) -> list[tuple[str, str]]:
        """Extract path parameters with their types.

        Returns list of (param_name, python_type) tuples.
        """
        # Find all {param} in path
        param_names = re.findall(r"\{(\w+)\}", self.path)

        result = []
        for name in param_names:
            # Check for explicit override
            if name in self.params:
                type_str = self.params[name]
                python_type = self._map_param_type(type_str)
            else:
                # Infer from naming convention
                python_type = self._infer_param_type(name)

            result.append((name, python_type))

        return result

    def _map_param_type(self, type_str: str) -> str:
        """Map spec type to Python type."""
        mapping = {
            "int": "int",
            "string": "str",
            "uuid": "UUID",
            "bool": "bool",
        }
        return mapping.get(type_str, "str")

    def _infer_param_type(self, param_name: str) -> str:
        """Infer Python type from parameter name."""
        if param_name.endswith("_id"):
            return "int"
        if param_name.endswith("_uuid"):
            return "UUID"
        return "str"

    @classmethod
    def from_yaml(cls, name: str, data: dict[str, Any]) -> HandlerSpec:
        """Create HandlerSpec from raw YAML dict."""
        # Handle request that can be string or dict with model+variant
        request_data = data.get("request")
        if isinstance(request_data, dict):
            request = RequestSpec.model_validate(request_data)
        else:
            request = request_data  # str or None

        # Handle response that can be string or dict
        response_data = data.get("response")
        if isinstance(response_data, dict):
            response = ResponseSpec.model_validate(response_data)
        else:
            response = response_data  # str or None

        return cls(
            name=name,
            method=data.get("method", "GET"),
            path=data.get("path", "/"),
            request=request,
            response=response,
            status=data.get("status"),
            params=data.get("params", {}),
        )


class RouterConfig(BaseModel):
    """Router configuration (prefix, tags)."""

    prefix: str = ""
    tags: list[str] = Field(default_factory=list)
    async_handlers: bool = True

    model_config = {"extra": "forbid"}


class RouterSpec(BaseModel):
    """Full router specification."""

    config: RouterConfig
    handlers: list[HandlerSpec]

    model_config = {"extra": "forbid"}

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> RouterSpec:
        """Create RouterSpec from raw YAML dict."""
        # Support both top-level and nested 'rest' format
        if "rest" in data:
            config_data = data["rest"]
            # Handle nested router config if present
            router_config = config_data.get("router", config_data)
        else:
            config_data = data
            router_config = data

        handlers_data = config_data.get("handlers", data.get("handlers", {}))

        # Parse config
        config = RouterConfig(
            prefix=router_config.get("prefix", ""),
            tags=router_config.get("tags", []),
            async_handlers=router_config.get("async_handlers", True),
        )

        # Parse handlers
        handlers = [
            HandlerSpec.from_yaml(name, handler_data)
            for name, handler_data in handlers_data.items()
        ]

        return cls(config=config, handlers=handlers)

    @property
    def prefix(self) -> str:
        """Get router prefix."""
        return self.config.prefix

    @property
    def tags(self) -> list[str]:
        """Get router tags."""
        return self.config.tags

    def get_referenced_models(self) -> set[str]:
        """Get all model names referenced by handlers."""
        models = set()
        for handler in self.handlers:
            if handler.request:
                models.add(handler.request)
            if handler.response_model:
                models.add(handler.response_model)
        return models
