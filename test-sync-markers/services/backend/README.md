# Backend Service

FastAPI application with SQLAlchemy, Alembic, and REST endpoints.

## Database migrations

Run `services/backend/scripts/migrate.sh` to apply the latest Alembic migrations. The backend
container entrypoint should execute this script before launching the API server so that the
database schema stays in sync with the application code.

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
