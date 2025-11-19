# Backlog

## Spec-First API Generation — Future Improvements

### Readonly Fields Support

**Status**: TODO

**Description**: Уточнить поддержку `readonly` полей в генераторе. Решить, как правильно трактовать `readonly` поля (например, делать их необязательными в create/update схемах, выставлять `Field(..., const=True)` и т.д.) и расширить генератор, чтобы эти правила соблюдались автоматически.

**Current State**: Флаг `readonly` в `shared/spec/models.yaml` игнорируется генератором. Нужно вернуться к этой задаче после MVP.


### Split Routers by Service

**Status**: DONE

**Description**: Currently, `routers/rest.py` is a monolith containing all endpoints. This will become unmaintainable. We need to split generated routers into `shared/generated/routers/<service_name>/<tag>.py` so each service only imports what it needs.

### Custom Linter for Spec Enforcement

**Status**: DONE

**Description**: We need to ensure that agents (and devs) don't bypass the spec. A custom linter/AST script should run in CI/pre-commit to forbid:
1. Defining `BaseModel` subclasses inside `services/` (except migrations/tests).
2. Instantiating `APIRouter` manually inside `services/` (except the main app composition).

### Implement Controller Pattern for Generated Routers

**Status**: IN PROGRESS

**Description**: Currently, generated routers contain `raise NotImplementedError`. We need a pattern (e.g., Controller injection or Protocol) to allow implementing logic without editing the generated file, while still satisfying the linter.
- Forbid manual `APIRouter` definitions that don't match spec interfaces.
