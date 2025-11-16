#!/usr/bin/env python3
"""Synchronize docker-compose service blocks from services.yml templates."""

from __future__ import annotations

from scripts.lib.compose_blocks import (
    COMPOSE_TARGETS,
    ROOT,
    build_service_block,
    gather_templates,
    load_registry,
    replace_block,
)


def sync_target(target, registry) -> None:
    templates = gather_templates(registry, target.key)
    block_lines = build_service_block(templates, target.indent)
    compose_path = target.path
    lines = compose_path.read_text(encoding="utf-8").splitlines()
    new_lines = replace_block(lines, block_lines)
    compose_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated {compose_path.relative_to(ROOT)} with {len(block_lines)} managed lines")


def main() -> int:
    registry = load_registry()
    for target in COMPOSE_TARGETS:
        sync_target(target, registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
