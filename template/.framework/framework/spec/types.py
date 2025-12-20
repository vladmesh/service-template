"""Type system for spec validation.

Defines the formal grammar of types supported in models.yaml:
- Primitives: int, string, bool, float, datetime, uuid
- Complex: list, dict, optional, enum
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

# Primitive types supported by the generator
PRIMITIVE_TYPES = Literal["int", "string", "bool", "float", "datetime", "uuid"]


class PrimitiveType(BaseModel):
    """A primitive type like int, string, bool, etc."""

    type: PRIMITIVE_TYPES


class ListType(BaseModel):
    """A list type with inner element type."""

    type: Literal["list"]
    of: "TypeSpec"  # noqa: UP037 - Forward reference needed for recursion


class DictType(BaseModel):
    """A dictionary type with key and value types."""

    type: Literal["dict"]
    key: "TypeSpec"  # noqa: UP037 - Forward reference needed for recursion
    value: "TypeSpec"  # noqa: UP037 - Forward reference needed for recursion

    @model_validator(mode="after")
    def validate_key_type(self) -> DictType:
        """Ensure dict key is a primitive (typically string)."""
        if not isinstance(self.key, PrimitiveType):
            msg = "Dict key must be a primitive type (typically 'string')"
            raise ValueError(msg)
        return self


class OptionalType(BaseModel):
    """An optional type wrapping another type."""

    type: Literal["optional"]
    of: "TypeSpec"  # noqa: UP037 - Forward reference needed for recursion


class EnumType(BaseModel):
    """An enumeration type with a fixed set of string values."""

    type: Literal["enum"]
    values: list[str]
    default: str | None = None

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[str]) -> list[str]:
        """Ensure enum has at least 2 unique values."""
        if len(v) < 2:  # noqa: PLR2004 - Enum must have 2+ values by definition
            msg = "Enum must have at least 2 values"
            raise ValueError(msg)
        if len(v) != len(set(v)):
            msg = "Enum values must be unique"
            raise ValueError(msg)
        # Ensure all values are valid Python identifiers (for Enum class generation)
        for val in v:
            if not val.isidentifier() or val.startswith("_"):
                msg = (
                    f"Enum value '{val}' must be a valid identifier "
                    "(no spaces, no leading underscore)"
                )
                raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_default_in_values(self) -> EnumType:
        """Ensure default is one of the enum values."""
        if self.default is not None and self.default not in self.values:
            msg = f"Default '{self.default}' is not in enum values: {self.values}"
            raise ValueError(msg)
        return self


# TypeSpec is a discriminated union of all type variants
TypeSpec = Annotated[
    PrimitiveType | ListType | DictType | OptionalType | EnumType,
    Field(discriminator="type"),
]

# Rebuild models to resolve forward references
ListType.model_rebuild()
DictType.model_rebuild()
OptionalType.model_rebuild()

# TypeAdapter for parsing the discriminated union
_type_spec_adapter = TypeAdapter(TypeSpec)


def type_spec_to_python(spec: TypeSpec) -> str:
    """Convert TypeSpec to Python type annotation string."""
    if isinstance(spec, PrimitiveType):
        mapping = {
            "int": "int",
            "string": "str",
            "bool": "bool",
            "float": "float",
            "datetime": "AwareDatetime",
            "uuid": "UUID",
        }
        return mapping[spec.type]

    if isinstance(spec, ListType):
        inner = type_spec_to_python(spec.of)
        return f"list[{inner}]"

    if isinstance(spec, DictType):
        key = type_spec_to_python(spec.key)
        value = type_spec_to_python(spec.value)
        return f"dict[{key}, {value}]"

    if isinstance(spec, OptionalType):
        inner = type_spec_to_python(spec.of)
        return f"{inner} | None"

    if isinstance(spec, EnumType):
        # Enum types are generated as separate classes, referenced by name
        # The actual class name is determined at generation time
        return "str"  # Placeholder, actual enum class name added by generator

    msg = f"Unknown type spec: {spec}"
    raise ValueError(msg)


def type_spec_to_json_schema(spec: TypeSpec) -> dict[str, Any]:
    """Convert TypeSpec to JSON Schema."""
    if isinstance(spec, PrimitiveType):
        mapping = {
            "int": {"type": "integer"},
            "string": {"type": "string"},
            "bool": {"type": "boolean"},
            "float": {"type": "number"},
            "datetime": {"type": "string", "format": "date-time"},
            "uuid": {"type": "string", "format": "uuid"},
        }
        return mapping[spec.type]

    if isinstance(spec, ListType):
        return {"type": "array", "items": type_spec_to_json_schema(spec.of)}

    if isinstance(spec, DictType):
        return {
            "type": "object",
            "additionalProperties": type_spec_to_json_schema(spec.value),
        }

    if isinstance(spec, OptionalType):
        inner = type_spec_to_json_schema(spec.of)
        # JSON Schema nullable pattern
        return {**inner, "nullable": True}

    if isinstance(spec, EnumType):
        schema: dict[str, Any] = {"type": "string", "enum": spec.values}
        if spec.default is not None:
            schema["default"] = spec.default
        return schema

    msg = f"Unknown type spec: {spec}"
    raise ValueError(msg)


def parse_type_spec(data: dict[str, Any] | str) -> TypeSpec:
    """Parse raw YAML data into a TypeSpec.

    Handles both dict format and shorthand string format.
    """
    # Shorthand: just a string like "int" or "string"
    if isinstance(data, str):
        if data in ("int", "string", "bool", "float", "datetime", "uuid"):
            return PrimitiveType(type=data)  # type: ignore[arg-type]

        # Support list[type] shorthand for backward compatibility
        if data.startswith("list[") and data.endswith("]"):
            inner = data[5:-1]
            return ListType(type="list", of=parse_type_spec(inner))

        # Support dict[key,value] shorthand
        if data.startswith("dict[") and data.endswith("]"):
            inner = data[5:-1]
            parts = inner.split(",", 1)
            if len(parts) == 2:  # noqa: PLR2004
                key_type, value_type = parts[0].strip(), parts[1].strip()
                return DictType(
                    type="dict",
                    key=parse_type_spec(key_type),
                    value=parse_type_spec(value_type),
                )

        msg = f"Unknown type shorthand: '{data}'"
        raise ValueError(msg)

    # Full dict format
    type_name = data.get("type")
    if type_name is None:
        msg = "Field spec must have a 'type' key"
        raise ValueError(msg)

    # Use Pydantic's discriminated union to parse
    return _type_spec_adapter.validate_python(data)
