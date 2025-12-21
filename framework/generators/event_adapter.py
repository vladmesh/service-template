"""Event adapter generator for unified handlers.

Generates event_adapter.py that uses existing ControllerProtocol
instead of creating a separate EventsHandlerProtocol.
This is part of the unified handlers architecture.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator
from framework.generators.context import OperationContextBuilder


class EventAdapterGenerator(BaseGenerator):
    """Generate event adapters using unified controller protocols.

    Unlike EventHandlersGenerator, this generator:
    - Uses the same ControllerProtocol as REST handlers
    - Includes session management in generated handlers
    - Supports publish_on_success and publish_on_error
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize generator."""
        super().__init__(*args, **kwargs)
        self.context_builder = OperationContextBuilder()

    def generate(self) -> list[Path]:
        """Generate event adapters for all services with event operations."""
        generated_files = []

        # Group domains by service and collect event operations
        services_data: dict[str, dict] = {}

        for domain_key, domain in self.specs.domains.items():
            service_name, domain_name = domain_key.split("/")

            # Get operations that have events configured
            events_ops = domain.get_events_operations()
            if not events_ops:
                continue

            if service_name not in services_data:
                services_data[service_name] = {
                    "domains": [],
                    "imports": set(),
                }

            protocol_name = f"{domain_name.capitalize()}ControllerProtocol"
            handlers = []

            for operation in events_ops:
                ctx = self.context_builder.build_for_events(operation)

                # Only process operations with subscribe (incoming events)
                if not ctx.subscribe_channel:
                    continue

                handler_ctx = {
                    "name": ctx.name,
                    "subscribe_channel": ctx.subscribe_channel,
                    "publish_on_success_channel": ctx.publish_channel,
                    "publish_on_error_channel": ctx.publish_on_error_channel,
                    "message_model": ctx.input_model or "dict",
                    "return_type": ctx.return_type,
                }
                handlers.append(handler_ctx)

                # Collect imports
                services_data[service_name]["imports"].update(ctx.imports)

            if handlers:
                services_data[service_name]["domains"].append(
                    {
                        "name": domain_name,
                        "protocol_name": protocol_name,
                        "handlers": handlers,
                    }
                )

        # Generate event_adapter.py for each service with event handlers
        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701
        )
        template = env.get_template("event_adapter.py.j2")

        for service_name, data in services_data.items():
            if not data["domains"]:
                continue

            output_file = (
                self.repo_root
                / "services"
                / service_name
                / "src"
                / "generated"
                / "event_adapter.py"
            )

            content = template.render(
                service_name=service_name,
                domains=data["domains"],
                imports=data["imports"],
            )
            self.write_file(output_file, content)
            self.format_file(output_file)
            generated_files.append(output_file)

        return generated_files
