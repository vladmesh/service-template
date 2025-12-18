"""Controller stub generator.

Generates controller stubs only if they don't exist.
For Phase 3, we add auto-stubbing of missing methods.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator


class ControllersGenerator(BaseGenerator):
    """Generate controller stubs for services."""

    def generate(self) -> list[Path]:
        """Generate controller stubs (only if not existing)."""
        generated = []

        for router_key, router in self.specs.routers.items():
            service_name, module_name = router_key.split("/")
            output_file = (
                self.repo_root
                / "services"
                / service_name
                / "src"
                / "controllers"
                / f"{module_name}.py"
            )

            # Only generate if file doesn't exist
            if output_file.exists():
                continue

            self._generate_controller(router, module_name, output_file)
            generated.append(output_file)

        return generated

    def _generate_controller(self, router, module_name: str, output_file: Path) -> None:
        """Generate a single controller stub."""
        handlers = []
        imports: set[str] = set()

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
                imports.add(handler.request_model)

            # Response model
            if handler.response_model:
                model = handler.response_model
                if handler.response_many:
                    handler_ctx["response_model"] = f"list[{model}]"
                    handler_ctx["return_type"] = f"list[{model}]"
                else:
                    handler_ctx["response_model"] = model
                    handler_ctx["return_type"] = model
                imports.add(model)

            handlers.append(handler_ctx)

        context = {
            "module_name": module_name,
            "protocol_name": f"{module_name.capitalize()}ControllerProtocol",
            "handlers": handlers,
            "imports": imports,
            "async_handlers": router.config.async_handlers,
        }

        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701
        )
        template = env.get_template("controller.py.j2")

        content = template.render(**context)
        # Controllers are editable, don't add generated header
        self.write_file(output_file, content, add_header=False)
        self.format_file(output_file)
