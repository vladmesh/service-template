# Service Template Framework

A rigid, spec-first, modular framework for building AI-Agent-ready microservices.

> **Start here:** Read the [MANIFESTO](MANIFESTO.md) to understand the philosophy behind this project.

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

## Development Workflow

- **Add Service:** Edit `services.yml` -> `make sync-services create`
- **Update API:** Edit `shared/spec/*.yaml` -> `make generate-from-spec`
- **Run Tests:** `make tests`
- **Lint:** `make lint`

## Documentation

- **[MANIFESTO.md](MANIFESTO.md)**: The core philosophy.
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: How it works under the hood.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Coding standards and rules.
- **[AGENTS.md](AGENTS.md)**: Navigation guide for AI agents.

### Template Development

- **[docs/TEMPLATE_DEVELOPMENT.md](docs/TEMPLATE_DEVELOPMENT.md)**: How to develop and extend the template.
- **[docs/TESTING.md](docs/TESTING.md)**: How to run template tests.

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
