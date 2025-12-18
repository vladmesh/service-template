"""Router generator using Jinja2 templates."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator
from framework.spec.routers import HandlerSpec, RouterSpec


class RoutersGenerator(BaseGenerator):
    """Generate FastAPI routers from router specs."""

    def generate(self) -> list[Path]:
        """Generate routers for all services."""
        generated = []

        for router_key, router_spec in self.specs.routers.items():
            # router_key is like "backend/users"
            service_name, router_name = router_key.split("/")

            # Target: services/<service_name>/src/generated/routers/<router_name>.py
            output_file = (
                self.repo_root
                / "services"
                / service_name
                / "src"
                / "generated"
                / "routers"
                / f"{router_name}.py"
            )

            self._generate_router(router_spec, router_name, output_file)
            generated.append(output_file)

        return generated

    def _generate_router(self, router: RouterSpec, module_name: str, output_file: Path) -> None:
        """Generate a single router file."""
        context = self._prepare_context(router, module_name)

        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701 - Generating Python code
        )
        template = env.get_template("router.py.j2")

        content = template.render(**context)
        self.write_file(output_file, content)
        self.format_file(output_file)

    def _prepare_context(self, router: RouterSpec, module_name: str) -> dict:
        """Prepare Jinja2 template context from router spec."""
        imports: set[str] = set()
        handlers = []

        for handler in router.handlers:
            handler_ctx = self._prepare_handler_context(handler, imports)
            handlers.append(handler_ctx)

        return {
            "module_name": module_name,
            "prefix": router.prefix,
            "tags": router.tags,
            "async_handlers": router.config.async_handlers,
            "imports": imports,
            "handlers": handlers,
            "protocol_name": f"{module_name.capitalize()}ControllerProtocol",
        }

    def _prepare_handler_context(self, handler: HandlerSpec, imports: set[str]) -> dict:
        """Prepare context for a single handler."""
        ctx = {
            "name": handler.name,
            "method": handler.method,
            "path": handler.path,
            "status_code": handler.status_code,
            "docstring": f"Handler for {handler.name}",
            "params": [],
            "request_model": None,
            "response_model": None,
            "return_type": "None",
        }

        # Path params
        for param_name, param_type in handler.get_path_params():
            ctx["params"].append(
                {
                    "name": param_name,
                    "type": param_type,
                    "source": "Path(...)",
                }
            )

        # Request model
        if handler.request_model:
            ctx["request_model"] = handler.request_model
            imports.add(handler.request_model)

        # Response model
        if handler.response_model:
            model = handler.response_model
            if handler.response_many:
                ctx["response_model"] = f"list[{model}]"
                ctx["return_type"] = f"list[{model}]"
            else:
                ctx["response_model"] = model
                ctx["return_type"] = model
            imports.add(model)

        return ctx
