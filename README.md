# service-template

**service-template** is an opinionated starter kit for small–to–mid sized backend services.

It’s designed to solve one concrete problem:

> “I don’t want to spend 4–5 hours every time wiring the same FastAPI + Postgres + Docker + CI/CD skeleton.”

You fork it, tweak it, remove modules you don’t need, and start building your actual product.

---

## Features

* **Fully containerized** – nothing installed locally except Docker.
* **FastAPI backend** with SQLAlchemy and Alembic migrations.
* **PostgreSQL** as the primary database.
* **Caddy** as reverse proxy (dev & prod).
* Optional **Telegram bot** as the first client.
* Optional **frontend** (Astro/React/etc.).
* **Docker Compose overlays** for:

  * base
  * development
  * tests
  * production
* Built-in:

  * **linting** (ruff)
  * **testing** (pytest)
  * CI hooks for PRs and main branch

---

## Tech Stack

* **Backend:** Python, FastAPI, SQLAlchemy, Alembic
* **Database:** PostgreSQL
* **Proxy:** Caddy
* **Frontend (optional):** Astro / React
* **Bot (optional):** Telegram bot
* **Testing:** pytest
* **Linting:** ruff
* **Containers:** Docker, Docker Compose
* **CI/CD:** GitHub Actions

---

## Repository Structure

```
.
├── apps/
│   ├── backend/
│   │   └── tests/
│   ├── tg_bot/
│   │   └── tests/
│   └── frontend/
│
├── infra/
│   ├── compose.base.yml
│   ├── compose.dev.yml
│   ├── compose.tests.unit.yml
│   ├── compose.tests.integration.yml
│   ├── compose.prod.yml
│   └── compose.frontend.yml
│
├── tests/        # cross-service integration suites
├── Makefile or justfile
├── .env.example
└── README.md
```

You are expected to delete modules you don’t need.

---

## Development Workflow

All day-to-day commands are exposed via the `Makefile`. Each target shells out to Docker Compose so that you never have to install tooling locally beyond Docker itself.

Common targets:

* `make dev-start` / `make dev-stop` — bring the dev stack up or down (`infra/compose.dev.yml` overlay).
* `make lint`, `make format`, `make typecheck` — run ruff/mypy inside the backend unit test container.
* `make tests` — run every unit suite (backend, tg_bot, and future services) plus the cross-service integration tests inside Docker Compose.
* `make tests backend` / `make tests tg_bot` — run a single service’s unit test suite (all executed inside Docker containers).
* `make tests integration` — start the integration Compose stack (backend + Postgres + deps) and run `tests/integration`.
* `make makemigrations name="add_users"` — generate Alembic revisions via the backend container so that migrations are reproducible.

The backend container now runs `apps/backend/scripts/migrate.sh` automatically during startup (both dev and prod overlays), so schema changes are always applied before Uvicorn comes up.

Follow the same pattern when you add new services: every module can have its own `test-<service>` unit target plus optional integration coverage driven by Compose profiles.

---

### Dependency management

Each Python service is its own Poetry project (for example, `apps/backend/pyproject.toml` and
`apps/tg_bot/pyproject.toml`). Install dependencies by running Poetry inside the respective
service directory. The backend image installs only runtime dependencies by default; Docker builds
meant for tests enable the optional dev group so `pytest` and the linting stack are available
without bloating production images.

---

## Modules

### Core

**Backend**: FastAPI, SQLAlchemy, Alembic, structured project layout.

**Database**: PostgreSQL with isolated networks in prod.

**Caddy**: reverse proxy routing API + frontend.

---

### Telegram Bot (optional)

* Lives in `apps/tg_bot`.
* Talks to backend via HTTP.
* Included in the base Compose stack.

Remove by deleting:

* `apps/tg_bot/`
* the `tg_bot` service block in `infra/compose.base.yml`

---

### Frontend (optional)

* Lives in `apps/frontend`.
* Served as its own container.
* Enabled via `compose.frontend.yml`.

---

## Docker & Compose

All environments are built from a shared base.

### Base

Defines backend, db, caddy, tg_bot.

### Development

Use volumes, exposed ports, hot reload.

```
docker compose \
  -f infra/compose.base.yml \
  -f infra/compose.dev.yml \
  up
```

Add modules as needed.

### Tests

Unit suites run through `infra/compose.tests.unit.yml`:

```
docker compose \
  -f infra/compose.tests.unit.yml \
  run --rm backend-tests-unit

docker compose \
  -f infra/compose.tests.unit.yml \
  run --rm tg-bot-tests-unit
```

Cross-service integration tests live under `tests/integration` and leverage `infra/compose.tests.integration.yml`:

```
docker compose \
  -f infra/compose.tests.integration.yml \
  up --build --abort-on-container-exit --exit-code-from integration-tests integration-tests

docker compose \
  -f infra/compose.tests.integration.yml \
  down --volumes --remove-orphans
```

`make tests` drives the exact same commands and adds simple switches for `backend`, `tg_bot`, `integration`, or `frontend` once the latter is implemented.

### Production

Uses prebuilt images and no source mounts.

```
docker compose \
  -f infra/compose.base.yml \
  -f infra/compose.prod.yml \
  pull

docker compose \
  -f infra/compose.base.yml \
  -f infra/compose.prod.yml \
  up -d
```

---

## Linting & Formatting

* **ruff** for linting/formatting.
* **mypy** optional.

---

## Testing

* pytest
* Unit + API integration tests
* Test DB fixtures
* Unit tests live inside each service (`apps/<service>/tests/unit`) and run through `make tests <service>` (for example, `make tests backend`).
* Cross-service integration suites live under `tests/integration` and run through `make tests integration` (or `make tests` to execute everything).

---

## CI/CD

Two GitHub Actions workflows are included out of the box:

* `.github/workflows/pr.yml` &mdash; runs `make lint` + `make tests` (Dockerized) for each pull request.
* `.github/workflows/main.yml` &mdash; builds/pushes the backend (and optional modules) and triggers a remote `docker compose up` via SSH.

Configuration details, required secrets, and troubleshooting tips live in [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md).

---

## Configuration & Secrets

Use `.env.example` and GitHub Secrets.

---

## Using This Template

1. Fork repository.
2. Delete modules you don’t need.
3. Adjust infra.
4. Build your actual service.

---
