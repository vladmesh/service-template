# Backend Service

Placeholder for backend service implementation.

## Database migrations

Run `apps/backend/scripts/migrate.sh` to apply the latest Alembic migrations. The backend
container entrypoint should execute this script before launching the API server so that the
database schema stays in sync with the application code.
