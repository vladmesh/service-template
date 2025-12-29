"""Client generator for typed REST clients.

Generates typed HTTP clients for consumer services based on manifest.consumes.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from framework.generators.base import BaseGenerator
from framework.generators.context import OperationContextBuilder


class ClientsGenerator(BaseGenerator):
    """Generate typed REST clients from manifest.consumes."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize generator."""
        super().__init__(*args, **kwargs)
        self.context_builder = OperationContextBuilder()

    def generate(self) -> list[Path]:
        """Generate clients for all services with manifests."""
        generated = []

        for service_name, manifest in self.specs.manifests.items():
            if not manifest.consumes:
                continue

            # Group consumes by provider service
            provider_domains: dict[str, list] = {}

            for consume in manifest.consumes:
                provider = consume.service
                domain_key = f"{consume.service}/{consume.domain}"

                if domain_key not in self.specs.domains:
                    continue  # Validation should catch this

                domain = self.specs.domains[domain_key]

                if provider not in provider_domains:
                    provider_domains[provider] = []

                # Filter operations if specific ones listed
                ops = domain.get_rest_operations()
                if consume.operations:
                    ops = [op for op in ops if op.name in consume.operations]

                if ops:
                    provider_domains[provider].append(
                        {
                            "domain": domain,
                            "operations": ops,
                        }
                    )

            # Generate client file for each provider
            for provider, domains_data in provider_domains.items():
                output_file = (
                    self.repo_root
                    / "services"
                    / service_name
                    / "src"
                    / "generated"
                    / "clients"
                    / f"{provider}.py"
                )

                self._generate_client(
                    provider=provider,
                    consumer=service_name,
                    domains_data=domains_data,
                    output_file=output_file,
                )
                generated.append(output_file)

            # Generate clients/__init__.py
            if provider_domains:
                init_file = (
                    self.repo_root
                    / "services"
                    / service_name
                    / "src"
                    / "generated"
                    / "clients"
                    / "__init__.py"
                )
                self._generate_clients_init(
                    providers=list(provider_domains.keys()),
                    output_file=init_file,
                )
                generated.append(init_file)

        return generated

    def _generate_client(
        self,
        provider: str,
        consumer: str,
        domains_data: list,
        output_file: Path,
    ) -> None:
        """Generate a single client file for a provider service."""
        context = self._prepare_context(provider, domains_data)

        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # noqa: S701 - Generating Python code
        )
        template = env.get_template("client.py.j2")

        content = template.render(**context)
        self.write_file(output_file, content)
        self.format_file(output_file)

    def _prepare_context(self, provider: str, domains_data: list) -> dict:
        """Prepare Jinja2 template context."""
        imports: set[str] = set()
        domains_context = []

        for data in domains_data:
            domain = data["domain"]
            operations = data["operations"]

            # Get domain prefix
            prefix = ""
            if domain.config.rest:
                prefix = domain.config.rest.prefix

            ops_context = []
            for op in operations:
                ctx = self.context_builder.build_for_rest(op)

                op_ctx = {
                    "name": ctx.name,
                    "http_method": ctx.http_method.lower() if ctx.http_method else "get",
                    "path": ctx.path or "",
                    "params": [{"name": p.name, "type": p.type} for p in ctx.params],
                    "input_model": ctx.input_model,
                    "output_model": ctx.output_model,
                    "return_type": ctx.computed_return_type,
                    "status_code": ctx.status_code,
                }

                imports.update(ctx.imports)
                ops_context.append(op_ctx)

            domains_context.append(
                {
                    "name": domain.name,
                    "prefix": prefix,
                    "operations": ops_context,
                }
            )

        return {
            "provider": provider,
            "provider_capitalized": provider.replace("_", " ").title().replace(" ", ""),
            "provider_upper": provider.upper(),
            "imports": imports,
            "domains": domains_context,
        }

    def _generate_clients_init(self, providers: list[str], output_file: Path) -> None:
        """Generate __init__.py for clients package."""
        lines = ['"""Generated clients for consumed services."""', ""]

        for provider in sorted(providers):
            class_name = provider.replace("_", " ").title().replace(" ", "") + "Client"
            lines.append(f"from .{provider} import {class_name}")

        lines.append("")
        lines.append("__all__ = [")
        for provider in sorted(providers):
            class_name = provider.replace("_", " ").title().replace(" ", "") + "Client"
            lines.append(f'    "{class_name}",')
        lines.append("]")
        lines.append("")

        content = "\n".join(lines)
        self.write_file(output_file, content)
        self.format_file(output_file)
