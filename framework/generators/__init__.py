# noqa: D104
"""Code generators for spec-first development."""

from framework.generators.base import BaseGenerator
from framework.generators.clients import ClientsGenerator
from framework.generators.controllers import ControllersGenerator
from framework.generators.event_adapter import EventAdapterGenerator
from framework.generators.events import EventsGenerator
from framework.generators.protocols import ProtocolsGenerator
from framework.generators.registry import RegistryGenerator
from framework.generators.routers import RoutersGenerator

try:
    from framework.generators.schemas import SchemasGenerator
except ImportError:
    SchemasGenerator = None  # type: ignore[assignment, misc]

__all__ = [
    "BaseGenerator",
    "ClientsGenerator",
    "SchemasGenerator",
    "RoutersGenerator",
    "ProtocolsGenerator",
    "ControllersGenerator",
    "EventsGenerator",
    "EventAdapterGenerator",
    "RegistryGenerator",
]
