# Contributing Guidelines

We adhere to a strict set of rules to maintain quality and consistency. These rules are enforced by CI and the `make` commands.

## 1. The Golden Rule: Use the Makefile
Never run tools directly. Always use the `make` target.
- `make lint`: Runs all linters.
- `make format`: Runs auto-formatters.
- `make tests`: Runs the test suite.
- `make sync-services`: Scaffolds new services.

## 2. Code Style & Standards
We use `ruff` for linting and formatting, and `mypy` for static typing.

- **Naming:**
    - Use `snake_case` for variables, functions, and file names.
    - Avoid `camelCase`.
- **Typing:**
    - All functions must have type hints.
    - `mypy` is configured with `disallow_untyped_defs`.
- **Imports:**
    - Absolute imports are preferred.
    - Sort imports (handled by `ruff`).

## 3. Workflow for Agents & Humans

### Adding a New Service
1.  Add entry to `services.yml`.
2.  Run `make sync-services create`.
3.  Implement the business logic in the generated `services/<name>/` directory.

### Modifying the API
1.  Edit `shared/spec/models.yaml` or `shared/spec/rest.yaml`.
2.  Run `make generate-from-spec`.
3.  Update service code to use the new generated models/routers.

### Testing
- **Unit Tests:** Each service has its own `tests/` folder.
- **Integration Tests:** Shared tests in the root `tests/` folder.
- **Coverage:** We aim for high test coverage.

## 4. "Read-Only" Zones
Do not manually edit files in these directories, as they are overwritten by scripts:
- `shared/generated/`
- `services/<name>/` (only specific files like `src/` should be edited; structural files like `Dockerfile` are templated, though currently managed manually after creation - *check templates if you need to change infrastructure*).

