# Backend Service

FastAPI application with SQLAlchemy, Alembic, and REST endpoints.

## Database migrations

Use the root Makefile for migrations:

```bash
make makemigrations name="describe_change"
make migrate
```

By default both targets start the dev PostgreSQL container and run Alembic inside a one-off
backend container. `make makemigrations` first upgrades the database to the current migration head,
then runs autogeneration. The generated revision is written to
`services/backend/migrations/versions/` through the dev bind mount.

If Docker is not available, use an already running PostgreSQL instance and the backend venv:

```bash
uv sync --project services/backend
make SKIP_INFRA_START=1 POSTGRES_HOST=localhost POSTGRES_PORT=5432 makemigrations name="describe_change"
make SKIP_INFRA_START=1 POSTGRES_HOST=localhost POSTGRES_PORT=5432 migrate
```

Use `POSTGRES_HOST=db` instead of `localhost` when `db` resolves from the current environment.
`DATABASE_URL=...` can also be passed as a make variable.

The backend container entrypoint runs `services/backend/scripts/migrate.sh` before launching
the API server, so `make dev-start` also applies the latest migrations.

## Using Generated Models and Routers

The backend uses spec-first API generation. Models and router stubs are generated from YAML specifications in `shared/spec/`.

### Generated Models

Import Pydantic models from `shared.generated.schemas`:

```python
from shared.generated.schemas import User, UserCreate, UserUpdate, UserPublic
```

Models are generated from `shared/spec/models.yaml`. Each model can have variants (e.g., `Create`, `Update`, `Public`) defined in the spec.

### Generated Routers

The REST router stub is generated in `shared/generated/routers/rest.py`. Import and use it:

```python
from shared.generated.routers.rest import router as generated_router

# Include in your FastAPI app
app.include_router(generated_router)
```

Handler functions in the generated router raise `NotImplementedError` by default — implement them in your service code or override them.

### Updating Specifications

1. Edit `shared/spec/models.yaml` or `shared/spec/rest.yaml`.
2. Run `make generate-from-spec` to regenerate code.
3. Commit both spec changes and generated files together.

CI will fail if generated files are out of sync with specifications.
