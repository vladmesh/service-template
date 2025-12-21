"""Registry generator for auto-registration of routers and event adapters.

Generates registry.py that centralizes all router registration,
eliminating manual boilerplate in router.py.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator


class RegistryGenerator(BaseGenerator):
    """Generate registry.py for each service with REST/Events operations.

    The registry provides:
    - create_api_router(): Creates and includes all domain routers
    - Imports for all protocols (for type hints in user code)
    """

    def generate(self) -> list[Path]:
        """Generate registry.py for all services with operations."""
        generated_files = []

        # Group domains by service
        services_data: dict[str, dict] = {}

        for domain_key, domain in self.specs.domains.items():
            service_name, domain_name = domain_key.split("/")

            # Check what operations this domain has
            rest_ops = domain.get_rest_operations()
            has_rest = bool(rest_ops)

            # Check if any REST operation publishes events
            has_rest_events = any(op.events for op in rest_ops) if has_rest else False

            has_events_subscribe = any(
                op.events and op.events.subscribe for op in domain.get_events_operations()
            )

            if not has_rest and not has_events_subscribe:
                continue

            if service_name not in services_data:
                services_data[service_name] = {
                    "domains": [],
                    "has_event_adapter": False,
                    "has_rest_events": False,
                    "protocol_imports": set(),
                }

            protocol_name = f"{domain_name.capitalize()}ControllerProtocol"

            domain_ctx = {
                "name": domain_name,
                "protocol_name": protocol_name,
                "has_rest": has_rest,
                "has_events": has_rest_events,
            }

            services_data[service_name]["domains"].append(domain_ctx)
            services_data[service_name]["protocol_imports"].add(protocol_name)

            if has_rest_events:
                services_data[service_name]["has_rest_events"] = True

            if has_events_subscribe:
                services_data[service_name]["has_event_adapter"] = True

        # Generate registry.py for each service
        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701
        )
        template = env.get_template("registry.py.j2")

        for service_name, data in services_data.items():
            # Only generate if there are domains with REST operations
            rest_domains = [d for d in data["domains"] if d["has_rest"]]
            if not rest_domains:
                continue

            output_file = (
                self.repo_root / "services" / service_name / "src" / "generated" / "registry.py"
            )

            content = template.render(
                service_name=service_name,
                domains=rest_domains,
                protocol_imports=sorted(data["protocol_imports"]),
                has_event_adapter=data["has_event_adapter"],
                has_rest_events=data["has_rest_events"],
            )
            self.write_file(output_file, content)
            self.format_file(output_file)
            generated_files.append(output_file)

        return generated_files
