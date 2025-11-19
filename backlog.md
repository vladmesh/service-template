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

**Status**: TODO

**Description**: Create a custom linter (e.g., Ruff plugin or AST script) to prevent agents/developers from bypassing the spec.
- Forbid defining Pydantic models in services (must use `shared.generated`).
- Forbid manual `APIRouter` definitions that don't match spec interfaces.
