# Backlog

## Spec-First API Generation — Future Improvements

### Readonly Fields Support

**Status**: TODO

**Description**: Уточнить поддержку `readonly` полей в генераторе. Решить, как правильно трактовать `readonly` поля (например, делать их необязательными в create/update схемах, выставлять `Field(..., const=True)` и т.д.) и расширить генератор, чтобы эти правила соблюдались автоматически.

**Current State**: Флаг `readonly` в `shared/spec/models.yaml` игнорируется генератором. Нужно вернуться к этой задаче после MVP.

