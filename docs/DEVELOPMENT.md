# Framework Development Guide

This document describes how to develop and contribute to the Service Template Framework itself.

> **Note**: This is for framework developers. If you're using the framework to build a product, see the generated project's README.

## Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Git
- Copier (`pip install copier`)

## Repository Structure

```
service-template/
├── docs/                 # Framework documentation (you are here)
├── framework/            # Framework source code (generators, validators)
├── tests/                # Framework tests
├── template/             # Product template (copied by Copier)
├── Makefile              # Framework development commands
└── README.md             # Framework usage documentation
```

## Development Workflow

### Running Tests

```bash
# Run all framework tests
make test

# Run specific test file
make test ARGS="-k test_generators"

# Run copier integration tests
make test-copier
```

### Linting

```bash
# Run all linters
make lint

# Auto-fix issues
make format
```

### Testing Template Generation

```bash
# Test copier template generation
make test-template

# Manual test: generate a project
copier copy . /tmp/test-project --force

# Verify generated project
cd /tmp/test-project
make lint
make test
```

## Key Components

### Generators (`framework/generators/`)

Code generators that transform YAML specs into Python code:

| Generator | Input | Output |
|-----------|-------|--------|
| `schemas.py` | `shared/spec/models.yaml` | Pydantic models |
| `routers.py` | `services/*/spec/*.yaml` | FastAPI routers |
| `protocols.py` | `services/*/spec/*.yaml` | Protocol classes |
| `clients.py` | `services/*/spec/manifest.yaml` | HTTP clients |
| `events.py` | `shared/spec/events.yaml` | FastStream pub/sub |

### Templates (`framework/templates/codegen/`)

Jinja2 templates used by generators to produce Python code.

### Spec Loaders (`framework/spec/`)

YAML spec parsers and validators.

## Syncing Framework to Template

The `framework/` code is duplicated in `template/.framework/` for product use. After making changes to `framework/`, sync them:

```bash
make sync-framework
```

This copies `framework/` contents to `template/.framework/`.

## Adding a New Generator

1. Create generator in `framework/generators/new_generator.py`
2. Create Jinja template in `framework/templates/codegen/new_template.py.j2`
3. Add entry point in `framework/generate.py`
4. Add tests in `tests/unit/test_generators.py`
5. Sync to template: `make sync-framework`
6. Update documentation

## Adding a New Module

Modules are pre-built services that ship with generated projects.

1. Create service in `template/services/new_module/`
2. Add entry in `template/services.yml.jinja`
3. Add Copier question in `copier.yml` (if selectable)
4. Add tests in `tests/copier/`
5. Update `template/AGENTS.md.jinja` with module documentation

## Release Process

1. Update version in `copier.yml`
2. Update CHANGELOG
3. Create git tag: `git tag v0.x.x`
4. Push tag: `git push --tags`

## Troubleshooting

### Copier shows "version None"
Ensure you have a git tag. Copier uses tags for versioning.

### Generated project imports fail
Check that `template/.framework/` is in sync with `framework/`.

### Tests fail after restructure
Verify all paths in `copier.yml`, tests, and Makefile are updated.
