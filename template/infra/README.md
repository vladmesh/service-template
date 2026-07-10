# Infrastructure contract

This directory contains the Docker Compose files that define the generated
project runtime. Keep these files compatible with two callers:

- local developers running `make dev-start`;
- external orchestrators that run generated projects as sibling containers and
  attach them to an already-created worker network.

## Service names

Compose service names are part of the project API. Other containers resolve
services by these DNS names on the default Compose network:

- `db` is PostgreSQL on port `5432` when the `backend` module is enabled.
- `redis` is Redis on port `6379` when `tg_bot` or `notifications` is enabled.
- `backend` is the FastAPI service on port `8000` when the `backend` module is
  enabled.
- `tg_bot`, `notifications_worker`, and `frontend` are the optional application
  services for their modules.

Do not rename these services without updating callers that use Compose DNS.
For example, generated defaults use `POSTGRES_HOST=db` and
`REDIS_URL=redis://redis:6379`.

## Network rules

Do not declare custom networks in these compose files and do not rename the
implicit `default` network. External worker managers may replace the generated
project's default network with a pre-created network shared with the worker
container. This lets the worker reach `db:5432`, `redis:6379`, and
`backend:8000` directly without Docker-in-Docker or host port forwarding.

## Compose modes

Worker mode uses the base and dev layers only:

```bash
docker compose -f infra/compose.base.yml -f infra/compose.dev.yml up -d --wait db redis
```

Pass only services that exist in the selected module set. Backend-only projects
have `db` but no `redis`; bot-only or notifications-only projects have `redis`
but no `db`.

Worker mode must not depend on published host ports. The dev layer keeps
services reachable on the Compose network, and the local-port layer is omitted.

Local developer mode adds published ports:

```bash
make dev-start
```

This expands to:

```bash
docker compose \
  -f infra/compose.base.yml \
  -f infra/compose.dev.yml \
  -f infra/compose.local.yml \
  up -d --build --wait
```

`infra/compose.local.yml` is the only layer that publishes development ports to
the host. Configure those ports in `.env`:

- `BACKEND_PORT` maps to `backend:8000`.
- `POSTGRES_HOST_PORT` maps to `db:5432`.
- `REDIS_HOST_PORT` maps to `redis:6379`.
- `FRONTEND_PORT` maps to `frontend:3000`.

Production mode uses:

```bash
docker compose -f infra/compose.base.yml -f infra/compose.prod.yml up -d --remove-orphans
```

Integration-test mode uses `infra/compose.tests.integration.yml` directly
through `make test-integration`.

## Healthchecks

Infrastructure services must have healthchecks. External orchestrators and the
generated Makefile use `docker compose up --wait`, so readiness is defined by
Compose health state, not by sleep loops.

Current required healthchecks:

- `db`: `pg_isready` against the configured database.
- `redis`: `redis-cli ping`.
- `backend`: HTTP `GET /health`.

Do not remove these healthchecks when changing service definitions. If a new
infrastructure service is added, give it a healthcheck before depending on it
from application services or orchestration code.

## Database and Redis environment

Environment priority depends on where the value is consumed:

1. Compose interpolation values, such as `${POSTGRES_HOST:-db}`, use the shell
   or command environment first, then generated `.env`, then the default in the
   compose file.
2. Container variables loaded with `env_file` come from generated `.env`.
3. Local `make` and Python commands use process environment first, then values
   exported from generated `.env`.

For local `make` targets, `.env` is included and exported by the generated
Makefile. Passing a variable on the command line overrides it, for example:

```bash
POSTGRES_HOST=custom-db make migrate
make POSTGRES_HOST=custom-db POSTGRES_PORT=6543 migrate
```

PostgreSQL can be configured by parts in Compose modes and by full URL for
local process commands:

- `POSTGRES_HOST` and `POSTGRES_PORT` select the host and port used to build
  Compose database URLs. The generated `.env` uses `db` and `5432`.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and
  `POSTGRES_REQUIRE_SSL` complete the generated URL.
- `DATABASE_URL` overrides the sync SQLAlchemy URL when backend code runs
  outside Compose.
- `ASYNC_DATABASE_URL` overrides the async SQLAlchemy URL when backend code runs
  outside Compose.

Use `POSTGRES_HOST=db` inside Compose worker/local modes. Use `localhost` or
another reachable host only when running backend tooling outside the Compose
network, for example with `SKIP_INFRA_START=1`. In worker/local Compose modes,
`DATABASE_URL` and `ASYNC_DATABASE_URL` are built by `compose.base.yml` from the
`POSTGRES_*` parts; shell values for the full URLs do not replace those service
environment entries.

Redis is configured by full URL:

- `REDIS_URL` is the application Redis endpoint. The generated `.env` uses
  `redis://redis:6379` when Redis is part of the selected modules.
- `TEST_REDIS_URL` overrides the Redis endpoint used by pytest fixtures.
- If `TEST_REDIS_URL` is not set, tests fall back to `TEST_REDIS_HOST` and
  `TEST_REDIS_PORT`, then to `localhost:6379`.

Use `REDIS_URL=redis://redis:6379` inside Compose worker/local modes. Use
`TEST_REDIS_URL` when Redis tests should target an isolated database or an
externally managed Redis instance. In worker/local Compose modes, Redis
consumers load `REDIS_URL` from generated `.env`; a shell `REDIS_URL=... docker
compose ...` invocation does not override the container value unless `.env` or
the compose service environment is changed.
