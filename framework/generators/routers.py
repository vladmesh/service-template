"""Router generator using Jinja2 templates and OperationContextBuilder."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator
from framework.generators.context import OperationContextBuilder


class RoutersGenerator(BaseGenerator):
    """Generate FastAPI routers from domain specs."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize generator."""
        super().__init__(*args, **kwargs)
        self.context_builder = OperationContextBuilder()

    def generate(self) -> list[Path]:
        """Generate routers for all services."""
        generated = []

        for domain_key, domain in self.specs.domains.items():
            service_name, domain_name = domain_key.split("/")

            # Only generate if domain has REST operations
            rest_ops = domain.get_rest_operations()
            if not rest_ops:
                continue

            output_file = (
                self.repo_root
                / "services"
                / service_name
                / "src"
                / "generated"
                / "routers"
                / f"{domain_name}.py"
            )

            self._generate_router(domain, domain_name, output_file)
            generated.append(output_file)

        return generated

    def _generate_router(self, domain, module_name: str, output_file: Path) -> None:
        """Generate a single router file."""
        context = self._prepare_context(domain, module_name)

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

    def _prepare_context(self, domain, module_name: str) -> dict:
        """Prepare Jinja2 template context from domain spec."""
        imports: set[str] = set()
        handlers = []

        # Get REST config from domain
        prefix = ""
        tags = []
        if domain.config.rest:
            prefix = domain.config.rest.prefix
            tags = domain.config.rest.tags

        for operation in domain.get_rest_operations():
            ctx = self.context_builder.build_for_rest(operation)

            handler_ctx = {
                "name": ctx.name,
                "method": ctx.http_method,
                "path": ctx.path,
                "status_code": ctx.status_code,
                "docstring": f"Handler for {ctx.name}",
                "params": [
                    {"name": p.name, "type": p.type, "source": p.source} for p in ctx.params
                ],
                "request_model": ctx.input_model,
                "response_model": ctx.computed_return_type if ctx.output_model else None,
                "return_type": ctx.computed_return_type,
            }

            imports.update(ctx.imports)
            handlers.append(handler_ctx)

        return {
            "module_name": module_name,
            "prefix": prefix,
            "tags": tags,
            "async_handlers": True,  # Always async in new format
            "imports": imports,
            "handlers": handlers,
            "protocol_name": f"{module_name.capitalize()}ControllerProtocol",
        }
