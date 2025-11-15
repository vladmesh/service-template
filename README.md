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
│   ├── tg_bot/
│   └── frontend/
│
├── infra/
│   ├── compose.base.yml
│   ├── compose.dev.yml
│   ├── compose.test.yml
│   ├── compose.prod.yml
│   ├── compose.tg.yml
│   └── compose.frontend.yml
│
├── tests/
├── Makefile or justfile
├── .env.example
└── README.md
```

You are expected to delete modules you don’t need.

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
* Enabled via `compose.tg.yml`.

Remove by deleting:

* `apps/tg_bot/`
* `infra/compose.tg.yml`

---

### Frontend (optional)

* Lives in `apps/frontend`.
* Served as its own container.
* Enabled via `compose.frontend.yml`.

---

## Docker & Compose

All environments are built from a shared base.

### Base

Defines backend, db, caddy.

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

```
docker compose \
  -f infra/compose.base.yml \
  -f infra/compose.test.yml \
  run --rm tests
```

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

---

## CI/CD

Two GitHub Actions workflows are included out of the box:

* `.github/workflows/pr.yml` &mdash; builds the Compose test stack and runs `ruff` + `pytest` for each pull request.
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
