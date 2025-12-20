# Service Template Framework

A rigid, spec-first, modular framework for building AI-Agent-ready microservices.

> **Start here:** Read the [MANIFESTO](docs/MANIFESTO.md) to understand the philosophy behind this project.

## Quick Start

### Create a New Project

```bash
# Install copier
pip install copier

# Generate a new project
copier copy gh:your-org/service-template my-project

# Or with specific modules
copier copy gh:your-org/service-template my-project \
  --data project_name=my-project \
  --data modules=backend,tg_bot
```

### Available Modules

| Module | Description |
|--------|-------------|
| `backend` | FastAPI REST API + PostgreSQL |
| `tg_bot` | Telegram bot (FastStream) |
| `notifications` | Email/Telegram notification worker |
| `frontend` | Node.js frontend |

### After Generation

```bash
cd my-project
cp .env.example .env
make dev-start
```

### Update Infrastructure

Pull latest infrastructure updates while preserving your code:

```bash
copier update
```

## Development Workflow (in Generated Projects)

After generating a project with `copier copy`:

- **Add Service:** Edit `services.yml` → `make sync-services create`
- **Update API:** Edit `shared/spec/*.yaml` → `make generate-from-spec`
- **Run Tests:** `make tests`
- **Lint:** `make lint`

## Framework Development

Developing the framework itself (this repository):

- **Run Tests:** `make test` (framework unit tests) or `make test-copier` (template generation tests)
- **Lint:** `make lint` (framework code only)
- **Sync `.framework/`:** `make sync-framework` (copy framework code to template)

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed framework development instructions.

## Documentation

### For Framework Users (Template Users)
- Generated projects include `README.md`, `AGENTS.md`, and `CONTRIBUTING.md` with usage instructions

### For Framework Developers
- **[docs/MANIFESTO.md](docs/MANIFESTO.md)**: The core philosophy
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: How the framework works
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**: How to develop the framework
- **[docs/RESTRUCTURING_PLAN.md](docs/RESTRUCTURING_PLAN.md)**: Current restructuring progress
- **[docs/backlog.md](docs/backlog.md)**: Framework roadmap

## Roadmap

1. **Current:** Copier-based updatable template with modular service selection.
2. **Next:** CLI wrappers for simplified usage (`my-framework init`, `my-framework sync`).
3. **Vision:** MCP server for AI agents to scaffold and manage services via API.

## Tech Stack

- **Core:** Python 3.12, Docker Compose
- **API:** FastAPI, Pydantic (Spec-First)
- **Data:** PostgreSQL, SQLAlchemy, Alembic
- **Messaging:** Redis, FastStream
- **Quality:** Ruff, Mypy, Pytest

## License

Open Source. Use it, fork it, build agents with it.
