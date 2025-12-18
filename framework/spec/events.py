"""Event specifications for async messaging validation.

Defines the structure of events.yaml:
- EventSpec: A single event definition
- EventsSpec: The root container for all events
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class EventSpec(BaseModel):
    """Specification for a single event."""

    name: str = ""  # Set by parent
    message: str  # Model name for the event payload
    publish: bool = False
    subscribe: bool = False

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_at_least_one_direction(self) -> EventSpec:
        """Ensure event is either publishable or subscribable."""
        if not self.publish and not self.subscribe:
            msg = f"Event '{self.name}' must have publish=true or subscribe=true (or both)"
            raise ValueError(msg)
        return self


class EventsSpec(BaseModel):
    """Root specification containing all events."""

    events: list[EventSpec] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @classmethod
    def from_yaml(cls, data: dict[str, Any] | None) -> EventsSpec:
        """Create EventsSpec from raw YAML dict."""
        if data is None:
            return cls(events=[])

        events_data = data.get("events", {})
        events = []

        for name, event_data in events_data.items():
            if not isinstance(event_data, dict):
                msg = f"Event '{name}' must be a dict"
                raise ValueError(msg)

            events.append(
                EventSpec(
                    name=name,
                    message=event_data.get("message", ""),
                    publish=event_data.get("publish", False),
                    subscribe=event_data.get("subscribe", False),
                )
            )

        return cls(events=events)

    def get_referenced_models(self) -> set[str]:
        """Get all model names referenced by events."""
        return {event.message for event in self.events if event.message}

    def get_publishers(self) -> list[EventSpec]:
        """Get events that can be published."""
        return [e for e in self.events if e.publish]

    def get_subscribers(self) -> list[EventSpec]:
        """Get events that can be subscribed to."""
        return [e for e in self.events if e.subscribe]
