# service-template

Container-first starter kit for building small and mid-sized backend services without repeating the same FastAPI + Postgres boilerplate. Fork it, drop the modules you do not need, and ship features right away.

## Services

- **backend** (`apps/backend`) — FastAPI application with SQLAlchemy, Alembic, and REST endpoints.
- **tg_bot** (`apps/tg_bot`) — optional Telegram bot that can talk to the backend.
- **frontend** (`apps/frontend`) — placeholder for any web UI you may add later.
- **tests** (`tests/`) — cross-service integration suites.

## Tech Stack

- Python 3.11, FastAPI, SQLAlchemy, Alembic
- PostgreSQL, Caddy
- Docker + Docker Compose overlays for dev/test/prod
- Ruff, Mypy, Pytest
- GitHub Actions pipelines (PR checks, verify-on-main, image builds, deploy hook)

## Makefile Cheatsheet

| Command | Description |
| --- | --- |
| `make dev-start` / `make dev-stop` | Bring the dev stack up/down (`infra/compose.dev.yml`). |
| `make lint` | Run Ruff checks inside the tooling container. |
| `make format` | Run Ruff formatter (also executed automatically by the pre-commit hook). |
| `make typecheck` | Run Mypy across `apps` and `tests`. |
| `make tests` | Execute backend + bot unit suites and shared integration tests (use `service=` or CLI args to scope). |
| `make makemigrations name="add_users"` | Generate Alembic migrations inside Docker. |

See [`AGENTS.md`](AGENTS.md) for workflow rules (always use `make`, never run code locally) and hook instructions.
