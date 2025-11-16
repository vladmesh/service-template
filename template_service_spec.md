# Microservice Template for Spec‑Driven Development

This canvas describes a unified template for a new microservice in your spec‑driven system:

* directory structure per service;
* a multi‑stage Dockerfile (runtime + test);
* docker‑compose blocks for dev/prod/test;
* how tests, dev and "prod" (runtime) environments are run.

All examples assume Python + Poetry, but the structure is language‑agnostic.

---

## 1. Microservice Directory Structure

Each service lives in its own directory:

```text
services/
  <service-name>/
    Dockerfile
    pyproject.toml        # or other dependency file, language‑specific
    poetry.lock           # optional, if using Poetry
    src/
      ... service source code ...
    tests/
      unit/
        ... unit tests (no real external deps) ...
      service/
        ... service‑level tests (need Postgres/Redis/etc.) ...
    AGENTS.md

# Integration / E2E tests live at project level, not inside a specific service
/tests/
  integration/
    ... cross‑service / end‑to‑end tests ...
```

**AGENTS.md** (per service) should contain:

* what the service does (role/purpose in the system);
* what it exposes: REST / RPC / events;
* which tools it provides to LLM agents (with input/output shapes).

Integration tests are **global**, not attached to a single service: they target the whole system and live under `tests/integration` at the project root.

---

## 2. Dockerfile Template (Multi‑Stage)

The Dockerfile is shared between runtime and tests via multiple build stages.

```Dockerfile
# syntax=docker/dockerfile:1

############################
# Base image
############################
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependency manager section – adjust if you don't use Poetry
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry \
    && poetry install --only main --no-root


############################
# Runtime image
############################
FROM base AS runtime

# Service source code
COPY src ./src

# Default environment – can be overridden by compose/spec
ENV APP_ENV=prod \
    APP_PORT=8000

# No default CMD here: runtime command is set by compose/spec
# Example (in compose):
#   command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


############################
# Test image
############################
FROM base AS test

# Install dev dependencies (linters, pytest, etc.)
RUN poetry install --with dev --no-root

# Copy code and tests
COPY src ./src
COPY tests ./tests

# No default CMD here either; tests are controlled by compose/CI
# Example (in compose or docker run):
#   command: ["pytest", "-m", "unit"]
#   command: ["pytest", "-m", "service"]
```

Key points:

* **one Dockerfile per service**;
* three stages: `base` (deps), `runtime` (prod), `test` (tests);
* test and runtime share the same dependency base, with extra dev deps only in `test`;
* no hardcoded `CMD` – commands are defined at the compose/spec level to stay spec‑driven.

---

## 3. docker‑compose Files and Service Blocks

At project level we use four compose files:

```text
./docker-compose.base.yml    # shared topology of services and infra
./docker-compose.dev.yml     # dev overrides
./docker-compose.prod.yml    # prod/runtime overrides
./docker-compose.test.yml    # test containers (service tests + integration tests)
```

> Note: `version:` is **omitted** in all compose files – it is deprecated in modern Docker Compose.

### 3.1. `docker-compose.base.yml`

Contains the shared structure: service names, networks, databases, caches, etc., but no concrete commands.

```yaml
services:
  <service-name>:
    image: <service-name>:latest
    networks:
      - app-net
    environment:
      APP_ENV: "base"   # overridden in other files

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - app-net

  redis:
    image: redis:7
    networks:
      - app-net

networks:
  app-net: {}

volumes:
  pgdata: {}
```

### 3.2. `docker-compose.dev.yml`

Dev environment: build `runtime` stage, mount source code, enable reload, dev env vars.

```yaml
services:
  <service-name>:
    build:
      context: ./services/<service-name>
      target: runtime
    environment:
      APP_ENV: "dev"
    volumes:
      - ./services/<service-name>/src:/app/src
    command: [
      "uvicorn", "app.main:app",
      "--host", "0.0.0.0",
      "--port", "8000",
      "--reload"
    ]
```

Dev run for a single service:

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.dev.yml \
  up <service-name>
```

Dev run for the whole stack:

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.dev.yml \
  up
```

### 3.3. `docker-compose.prod.yml`

Runtime/"prod" for local runs: build `runtime` stage, set prod env. The actual command comes from spec/compose.

```yaml
services:
  <service-name>:
    build:
      context: ./services/<service-name>
      target: runtime
    environment:
      APP_ENV: "prod"
    # Command is intentionally NOT baked into the image; define it here or in spec
    # command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Local "prod" run:

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.prod.yml \
  up -d --build
```

### 3.4. `docker-compose.test.yml`

Defines test containers for service‑level tests and project‑level integration tests.

```yaml
services:
  # Service-level tests for a specific service
  <service-name>-tests:
    build:
      context: ./services/<service-name>
      target: test
    depends_on:
      - postgres
      - redis
    environment:
      APP_ENV: "test"
    # Default command can be overridden when running
    command: ["pytest", "-m", "service"]

  # Global integration / E2E tests for the whole system
  tests-e2e:
    build:
      context: ./tests/integration
    depends_on:
      - <service-name>        # add all services that must be up
      - postgres
      - redis
    environment:
      APP_ENV: "test"

# Infra services (postgres, redis, etc.) are defined in base.yml
```

Service‑level tests for one service:

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.test.yml \
  run --rm <service-name>-tests pytest -m service
```

Global integration/E2E tests:

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.test.yml \
  run --rm tests-e2e
```

---

## 4. Test Strategy: Everything in Docker, Different Levels by Markers

Everything runs inside Docker, but we still distinguish **unit**, **service‑level**, and **integration** tests by semantics:

* **unit tests**

  * do not depend on real external services (no real Postgres/Redis/HTTP calls);
  * run inside the `test` image without needing `docker-compose` infra;
  * are fast and give localized feedback.

* **service‑level tests**

  * use real infra components from `docker-compose.base.yml` (Postgres/Redis/etc.);
  * still run inside the same `test` image, but with `depends_on` infra services;
  * are slower/more fragile but closer to real runtime behavior.

* **integration/E2E tests**

  * live in `/tests/integration` at project root;
  * talk to the whole system: multiple services + infra + mocks;
  * run via a dedicated `tests-e2e` container defined in `docker-compose.test.yml`.

### 4.1. Pytest markers

Example structure and markers:

```python
# services/<service-name>/tests/unit/test_something.py
import pytest

@pytest.mark.unit
def test_pure_function():
    ...


# services/<service-name>/tests/service/test_repository.py
import pytest

@pytest.mark.service
def test_repo_uses_real_db(db_session):
    ...
```

### 4.2. Example commands (no venvs on host)

**Unit tests for a service** (Docker only, no compose):

```bash
# Build test image
docker build -t <service-name>:test --target test ./services/<service-name>

# Run only unit tests
docker run --rm <service-name>:test pytest -m unit
```

**Service‑level tests** (test image + compose infra):

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.test.yml \
  run --rm <service-name>-tests pytest -m service
```

**Full test run for a service** (unit + service, still inside the same image):

```bash
docker run --rm <service-name>:test pytest -m "unit or service"
```

**Global integration/E2E tests**:

```bash
docker compose \
  -f docker-compose.base.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.test.yml \
  run --rm tests-e2e
```

---

## 5. Summary

Per‑service:

* `services/<service-name>/Dockerfile` with stages: `base`, `runtime`, `test`; **no CMD** baked in.
* `services/<service-name>/src/` – service code.
* `services/<service-name>/tests/` – `unit/` and `service/` tests.
* `services/<service-name>/AGENTS.md` – agent‑facing description and tools.

Project‑level:

* `docker-compose.base.yml` – shared topology of all services + infra.
* `docker-compose.dev.yml` – dev overrides (runtime target, reload, volumes).
* `docker-compose.prod.yml` – prod overrides (runtime target, prod env).
* `docker-compose.test.yml` – test services (`<service-name>-tests`, `tests-e2e`).
* `/tests/integration` – global integration/E2E tests.

This template is minimal but expressive enough to be spec‑driven: a YAML spec can

* generate the service directory skeleton;
* generate Dockerfile stages (runtime + test);
* add service blocks to base/dev/prod/test compose files;
* and wire in test commands and infra dependencies (unit/service/integration) per service.
