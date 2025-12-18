"""Protocol generator for controllers."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator


class ProtocolsGenerator(BaseGenerator):
    """Generate controller protocols from all routers."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize with output path."""
        super().__init__(*args, **kwargs)
        self.output_file = self.repo_root / "shared" / "shared" / "generated" / "protocols.py"

    def generate(self) -> list[Path]:
        """Generate protocols for all services."""
        generated_files = []

        # Group routers by service
        services_routers: dict[str, list] = {}
        services_imports: dict[str, set[str]] = {}

        for router_key, router in self.specs.routers.items():
            service_name, module_name = router_key.split("/")

            if service_name not in services_routers:
                services_routers[service_name] = []
                services_imports[service_name] = set()

            protocol_name = f"{module_name.capitalize()}ControllerProtocol"

            handlers = []
            for handler in router.handlers:
                handler_ctx = {
                    "name": handler.name,
                    "params": [],
                    "request_model": None,
                    "response_model": None,
                    "return_type": "None",
                }

                # Path params
                for param_name, param_type in handler.get_path_params():
                    handler_ctx["params"].append(
                        {
                            "name": param_name,
                            "type": param_type,
                        }
                    )

                # Request model
                if handler.request_model:
                    handler_ctx["request_model"] = handler.request_model
                    services_imports[service_name].add(handler.request_model)

                # Response model
                if handler.response_model:
                    model = handler.response_model
                    if handler.response_many:
                        handler_ctx["response_model"] = f"list[{model}]"
                        handler_ctx["return_type"] = f"list[{model}]"
                    else:
                        handler_ctx["response_model"] = model
                        handler_ctx["return_type"] = model
                    services_imports[service_name].add(model)

                handlers.append(handler_ctx)

            services_routers[service_name].append(
                {
                    "name": module_name,
                    "protocol_name": protocol_name,
                    "handlers": handlers,
                }
            )

        # Generate protocols.py for each service
        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=False,  # Keep indentation for protocol methods
            autoescape=False,  # noqa: S701
        )
        template = env.get_template("protocols.py.j2")

        for service_name, routers_context in services_routers.items():
            output_file = (
                self.repo_root / "services" / service_name / "src" / "generated" / "protocols.py"
            )

            content = template.render(
                routers=routers_context,
                imports=services_imports[service_name],
                async_handlers=True,
            )
            self.write_file(output_file, content)
            self.format_file(output_file)
            generated_files.append(output_file)

        return generated_files
