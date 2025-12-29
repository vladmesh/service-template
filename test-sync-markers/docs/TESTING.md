# Testing Guide

This document describes how to run tests for the service-template project.

## Test Categories

### 1. Unit Tests

Tests for the framework's core logic (`framework/spec/`):

```bash
make tests suite=unit
```

Covers:
- Spec parsing and validation
- Type system
- Model/Router/Event spec logic

### 2. Tooling Tests

Tests for the framework's CLI tools and generators (`framework/generators/`, `framework/openapi/`, etc.):

```bash
make tooling-tests
```

Covers:
- `sync_services.py` - Service scaffolding and synchronization
- `generate.py` - Modular code generation from YAML specs
- `openapi/generator.py` - OpenAPI export
- `frontend/generator.py` - TypeScript type generation
- `lint/controller_sync.py` - Controller synchronization check

### 2. Copier Template Tests

Tests for the Copier template generation:

```bash
COMPOSE_PROJECT_NAME=tooling docker compose -f infra/compose.tests.unit.yml \
  run --rm tooling pytest tests/copier/ -v
```

Covers:
- Project generation with different module combinations
- Conditional file inclusion/exclusion
- Docker Compose validity
- No Jinja artifacts in output
- `copier update` preserving user code

### 3. Service Unit Tests

Tests for individual services:

```bash
# All service tests
make tests

# Specific service
make tests suite=backend
make tests suite=tg_bot
```

### 4. Integration Tests

End-to-end tests with real services:

```bash
make tests suite=integration
```

## Running Tests

### All Tests

```bash
make tests
```

This runs:
1. All service unit tests
2. Tooling tests

### Specific Test Suite

```bash
# By service name
make tests service=backend
make tests suite=tg_bot

# Tooling only
make tests suite=tooling
# or
make tooling-tests
```

### With Coverage

Tooling tests include coverage by default (70% minimum):

```bash
make tooling-tests
```

Service tests also include coverage:

```bash
make tests suite=backend
# Outputs coverage report for services/backend/src/
```

## Copier Template Tests

### Test Structure

```
tests/copier/
├── __init__.py
└── test_template_generation.py
```

### Test Classes

| Class | Description |
|-------|-------------|
| `TestBackendOnlyGeneration` | Backend module only |
| `TestBackendWithTgBotGeneration` | Backend + tg_bot |
| `TestFullStackGeneration` | All modules |
| `TestEnvExample` | .env.example generation |
| `TestModuleExclusion` | Unselected modules excluded |
| `TestComposeServices` | Docker Compose generation |
| `TestIntegration` | Generated project validation |
| `TestCopierUpdate` | Update preserves user code |

### Running Specific Tests

```bash
# Single test class
COMPOSE_PROJECT_NAME=tooling docker compose -f infra/compose.tests.unit.yml \
  run --rm tooling pytest tests/copier/test_template_generation.py::TestBackendOnlyGeneration -v

# Single test method
COMPOSE_PROJECT_NAME=tooling docker compose -f infra/compose.tests.unit.yml \
  run --rm tooling pytest tests/copier/test_template_generation.py::TestComposeServices::test_redis_with_notifications -v
```

### What Template Tests Verify

1. **Core files exist** - Makefile, README.md, etc.
2. **Services correctly included/excluded** based on modules
3. **Docker Compose valid** - services, networks, volumes
4. **No Jinja artifacts** - no `{{`, `{%` in output
5. **Conditional content** - ARCHITECTURE.md, AGENTS.md adapt to modules
6. **Update behavior** - user code preserved on `copier update`

## Linting

```bash
make lint
```

Runs:
- `ruff check` - Python linting
- `xenon` - Complexity check
- `spec.loader` - YAML spec validation
- `enforce_spec_compliance` - Custom rules
- `lint.controller_sync` - Controller-protocol sync check

## Type Checking

```bash
make typecheck
```

Runs `mypy` on tests and services.

## CI Integration

Tests run automatically on:
- Push to `main` branch
- Pull requests

See `.github/workflows/verify.yml` for CI configuration.

## Debugging Failed Tests

### View Full Output

```bash
COMPOSE_PROJECT_NAME=tooling docker compose -f infra/compose.tests.unit.yml \
  run --rm tooling pytest tests/copier/ -v --tb=long
```

### Interactive Debugging

```bash
# Enter tooling container
COMPOSE_PROJECT_NAME=tooling docker compose -f infra/compose.tests.unit.yml \
  run --rm tooling bash

# Run tests interactively
pytest tests/copier/ -v -x --pdb
```

### Test Generated Project Manually

```bash
# Generate project
copier copy . /tmp/test-project \
  --data project_name=test \
  --data modules=backend,tg_bot \
  --trust --defaults

# Inspect
cd /tmp/test-project
cat services.yml
docker compose -f infra/compose.base.yml config
```

## Writing New Tests

### For Template Changes

Add tests to `tests/copier/test_template_generation.py`:

```python
@pytest.mark.usefixtures("copier_available")
class TestMyNewFeature:
    def test_feature_works(self, tmp_path: Path):
        output = run_copier(tmp_path, "backend,my_module")
        
        # Assert expected files exist
        assert (output / "services" / "my_module").exists()
        
        # Assert content is correct
        content = (output / "some_file.yml").read_text()
        assert "expected_content" in content
```

### For Framework Changes

Add tests to `tests/tooling/`:

```python
def test_my_framework_feature():
    # Test framework functionality
    result = my_function(input)
    assert result == expected
```
