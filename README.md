# service-template

Container-first starter kit for building small and mid-sized backend services without repeating the same FastAPI + Postgres boilerplate. Fork it, drop the modules you do not need, and ship features right away.

## Services

- **backend** (`services/backend`) — FastAPI application with SQLAlchemy, Alembic, and REST endpoints.
- **tg_bot** (`services/tg_bot`) — optional Telegram bot that can talk to the backend.
- **frontend** (`services/frontend`) — placeholder for any web UI you may add later.
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
| `make typecheck` | Run Mypy across `services` and `tests`. |
| `make tests` | Execute backend + bot unit suites and shared integration tests (use `service=` or CLI args to scope). |
| `make makemigrations name="add_users"` | Generate Alembic migrations inside Docker. |
| `make sync-services [create]` | Ensure `services.yml` artifacts exist (default `check`, add `create` to scaffold missing files). |
| `make tooling-tests` | Run sync-services/scaffolding pytest suites inside the tooling container. |

See [`AGENTS.md`](AGENTS.md) for workflow rules (always use `make`, never run code locally) and hook instructions.

## Adding a Service

1. Describe the service in `services.yml` (fields: `name`, `type`, `description`).
2. Run `make sync-services create` to scaffold the directory and Compose overlays inside containers.
3. Fill in the generated `README.md`, `AGENTS.md`, Dockerfile, and stub code/tests manually.
4. Commit the changes and run `make sync-services`, `make lint`, and `make tests` before opening a PR.
