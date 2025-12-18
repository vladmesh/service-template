"""Event handlers generator with Protocol pattern.

Generates EventsHandlerProtocol and event registration for services
that subscribe to events defined in their domain specs.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator


class EventHandlersGenerator(BaseGenerator):
    """Generate event handlers with Protocol pattern for services."""

    def generate(self) -> list[Path]:
        """Generate event handlers for services with event subscriptions."""
        generated = []

        # Group domains by service and collect event operations
        services_handlers: dict[str, list] = {}
        services_imports: dict[str, set[str]] = {}

        for domain_key, domain in self.specs.domains.items():
            service_name, _ = domain_key.split("/")

            # Get operations that have events configured
            events_ops = domain.get_events_operations()
            if not events_ops:
                continue

            if service_name not in services_handlers:
                services_handlers[service_name] = []
                services_imports[service_name] = set()

            for operation in events_ops:
                if operation.events and operation.events.subscribe:
                    handler_ctx = {
                        "name": operation.name,
                        "subject": operation.events.subscribe,
                        "message_model": operation.input_model or "dict",
                    }
                    services_handlers[service_name].append(handler_ctx)

                    if operation.input_model:
                        services_imports[service_name].add(operation.input_model)

        # Generate event_handlers.py for each service with subscriptions
        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701
        )
        template = env.get_template("event_handlers.py.j2")

        for service_name, handlers in services_handlers.items():
            if not handlers:
                continue

            output_file = (
                self.repo_root
                / "services"
                / service_name
                / "src"
                / "generated"
                / "event_handlers.py"
            )

            content = template.render(
                handlers=handlers,
                imports=services_imports[service_name],
            )
            self.write_file(output_file, content)
            self.format_file(output_file)
            generated.append(output_file)

        return generated
