# test-sync

A microservice project built with service-template framework

## Quick Start

1. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Start development**
   ```bash
   make dev-start
   ```

3. **Run tests**
   ```bash
   make tests
   ```

## Modules

This project includes the following modules:

- **backend** - FastAPI REST API with PostgreSQL
- **tg_bot** - Telegram bot (FastStream)


## Development Workflow

- **Add/modify models:** Edit `shared/spec/models.yaml` → `make generate-from-spec`
- **Add endpoints:** Edit `services/backend/spec/routers/*.yaml` → `make generate-from-spec`
- **Run linter:** `make lint`
- **Run formatter:** `make format`

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [CONTRIBUTING.md](CONTRIBUTING.md) - Coding standards
- [AGENTS.md](AGENTS.md) - AI agent navigation guide

## Tech Stack

- **Python** 3.12
- **FastAPI** + **Pydantic** (spec-first)
- **PostgreSQL** + **SQLAlchemy** + **Alembic**
- **Redis** + **FastStream** (async messaging)
- **Docker Compose** (containerized development)

---

*Generated with [service-template](https://github.com/your-org/service-template)*
